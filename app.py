import os
import asyncio
import json
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import StreamingResponse
from mcp_server import mcp
import google.generativeai as genai
from github_client import fetch_workflow_logs, get_workflow_run_status
from config import (
    GOOGLE_API_KEY, 
    SLACK_ID_VARUN, SLACK_ID_KHUSHI, SLACK_ID_MANAV,
    JIRA_USER_ID_VARUN, JIRA_USER_ID_KHUSHI, JIRA_USER_ID_MANAV,
    SMTP_USER, SMTP_PASS, SMTP_SERVER, SMTP_PORT, APPROVER_EMAIL, BASE_URL
)
from workflow_state import workflows, emit_event, subscribe, unsubscribe
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = FastAPI(title="MCP DevOps Webhook")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend static files
app.mount("/static", StaticFiles(directory="frontend"), name="static")

# Initialize Gemini
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel('gemini-flash-latest')
else:
    model = None
    print("Warning: GOOGLE_API_KEY not found. Agent analysis will be disabled.")

# Directory for log and analysis persistence
LOG_DIR = "logs"
ANALYSIS_DIR = "analysis"
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(ANALYSIS_DIR, exist_ok=True)


# ── SSE Streaming Endpoint ─────────────────────────

@app.get("/api/stream")
async def event_stream():
    queue = await subscribe()

    async def generate():
        try:
            while True:
                data = await queue.get()
                yield f"data: {json.dumps(data, default=str)}\n\n"
        except asyncio.CancelledError:
            await unsubscribe(queue)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── Dashboard & API Endpoints ──────────────────────

@app.get("/dashboard")
async def dashboard():
    return FileResponse("frontend/index.html")


@app.get("/api/workflows")
async def get_workflows():
    return workflows


@app.get("/api/workflows/{run_id}")
async def get_workflow(run_id: str):
    return wf


# ── Approval Helpers ────────────────────────────────

def send_approval_email(run_id: str, analysis: str, tools: list):
    """Send an HTML email with Approve/Reject links."""
    if not all([SMTP_USER, SMTP_PASS, APPROVER_EMAIL]):
        print(" [Email] SMTP not configured. Skipping email.")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🚀 Approval Required: Pipeline Failure in {run_id}"
    msg["From"] = SMTP_USER
    msg["To"] = APPROVER_EMAIL

    tools_list = "".join([f"<li>{t}</li>" for t in tools])
    approve_url = f"{BASE_URL}/api/approve/{run_id}"
    reject_url = f"{BASE_URL}/api/reject/{run_id}"

    html = f"""
    <html>
    <body style="font-family: sans-serif; line-height: 1.6; color: #333;">
        <h2 style="color: #d32f2f;">🚨 Pipeline Action Required</h2>
        <p>A failure was detected and analyzed. Your approval is needed to execute the following tools:</p>
        
        <div style="background: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
            <strong>Analysis:</strong><br>
            {analysis}
        </div>

        <strong>Planned Actions:</strong>
        <ul>{tools_list}</ul>

        <div style="margin-top: 30px;">
            <a href="{approve_url}" style="background: #2e7d32; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; margin-right: 10px; font-weight: bold;">✅ Approve & Execute</a>
            <a href="{reject_url}" style="background: #d32f2f; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; font-weight: bold;">❌ Reject & Skip</a>
        </div>
        
        <p style="font-size: 0.8em; color: #666; margin-top: 40px;">
            Run ID: {run_id}<br>
            Server: {BASE_URL}
        </p>
    </body>
    </html>
    """
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, APPROVER_EMAIL, msg.as_string())
        print(f" [Email] Approval email sent to {APPROVER_EMAIL}")
    except Exception as e:
        print(f" [Email] Failed to send email: {e}")


async def execute_planned_tools(run_id: str):
    """Resumes a workflow by executing the saved tool calls."""
    wf = workflows.get(run_id)
    if not wf: return

    # Load analysis for tool args
    analysis_path = os.path.join(ANALYSIS_DIR, f"{run_id}_analysis.json")
    if not os.path.exists(analysis_path):
        print(f" [Approval] Analysis file missing for {run_id}")
        await emit_event(run_id, "ERROR", {"error": "Analysis file missing"})
        return

    with open(analysis_path, "r") as f:
        decision = json.load(f)

    await emit_event(run_id, "APPROVED", {"message": "User approved actions."})

    for tool_call in decision.get("tools", []):
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]

        step_map = {
            "send_slack_notification": ("SENDING_SLACK", "SLACK_DONE"),
            "update_tracking_sheet": ("UPDATING_SHEET", "SHEET_DONE"),
            "create_jira_issue": ("CREATING_JIRA", "JIRA_DONE"),
        }
        start_step, done_step = step_map.get(tool_name, (f"RUNNING_{tool_name.upper()}", f"{tool_name.upper()}_DONE"))

        print(f" Executing MCP Tool: {tool_name}")
        await emit_event(run_id, start_step, {"tool": tool_name})

        if tool_name == "create_jira_issue":
            from mcp_server import create_jira_issue
            result = await asyncio.to_thread(create_jira_issue, **tool_args)
        elif tool_name == "send_slack_notification":
            from mcp_server import send_slack_notification
            result = await asyncio.to_thread(send_slack_notification, **tool_args)
        elif tool_name == "update_tracking_sheet":
            from mcp_server import update_tracking_sheet
            result = await asyncio.to_thread(update_tracking_sheet, **tool_args)

        await emit_event(run_id, done_step, {"tool": tool_name, "result": str(result)})

    await emit_event(run_id, "COMPLETED", {})


# ── Agent Workflow (instrumented with events) ──────

async def run_agent_workflow(status: str, repo: str, run_id: str, branch: str, logs_content: str = None):
    """
    The 'Brain' of the MCP Server.
    Now includes a polling loop to wait for the GitHub workflow to finalize.
    """
    # ── Step: Polling GitHub ──
    if "/" not in repo:
        owner, repo_name = "VarunChavda78", repo
    else:
        owner, repo_name = repo.split("/", 1)

    if not logs_content:
        print(f" Waiting for GitHub workflow {run_id} to complete...")
        await emit_event(run_id, "WAITING_FOR_GITHUB", {"message": "Waiting for GitHub to finalize logs..."})
        
        max_retries = 20  # ~7-10 minutes
        log_fetched = False
        
        for i in range(max_retries):
            try:
                run_status, conclusion = get_workflow_run_status(owner, repo_name, run_id)
                print(f" Run {run_id} status: {run_status} ({conclusion})")
                
                if run_status == "completed":
                    # Now fetch the real logs
                    print(f" Run {run_id} completed. Fetching logs...")
                    logs_content = fetch_workflow_logs(owner, repo_name, run_id)
                    log_fetched = True
                    break
            except Exception as e:
                print(f" Error checking status for {run_id}: {e}")
            
            await asyncio.sleep(20) # poll every 20s
            
        if not log_fetched:
            print(f" Timeout waiting for logs for {run_id}")
            await emit_event(run_id, "ERROR", {"error": "Timeout waiting for GitHub to finalize logs."})
            return

    # Once we have logs_content (either from param or from polling)
    # We now analyze ALL runs to find hidden errors, even if the status is success
    await emit_event(run_id, "LOGS_FETCHED", {"message": "Final logs received and unzipped."})
    print(f" Agent starting analysis for {repo} (Run: {run_id})")

    # ── Step: Analyzing with LLM ──
    await emit_event(run_id, "ANALYZING_LLM", {})

    prompt = f"""
    A CI/CD pipeline finished in repo '{repo}' on branch '{branch}' with Status: '{status.upper()}'.

    LOGS:
    {logs_content[:]}

    TEAM MEMBERS:
    - DevOps (Varun Chavda): Slack={SLACK_ID_VARUN}, JIRA={JIRA_USER_ID_VARUN}
    - Frontend (Manav Thakkar): Slack={SLACK_ID_MANAV}, JIRA={JIRA_USER_ID_MANAV}
    - Backend (Khushi Patel): Slack={SLACK_ID_KHUSHI}, JIRA={JIRA_USER_ID_KHUSHI}

    As a DevOps Agent, you have access to the following MCP TOOLS:
    1. send_slack_notification(message, user_id=None)
    2. update_tracking_sheet(task, owner, status)
    3. create_jira_issue(summary, description, assignee_id=None)

    DECIDE:
    1. Scan the logs for ANY issues (errors, warnings, or performance risks).
    2. HIDDEN ERROR ANALYSIS: Even if the status is SUCCESS, look for silent failures (retries, deprecation, non-fatal build errors).
    3. Categorize the findings: DevOps, Frontend, or Backend.
    4. Assign the correct team member (Varun, Manav, or Khushi).
    5. NOTIFICATION RULES:
       - If the status is FAILURE: ALWAYS notify Slack, update the sheet, and create a Jira issue.
       - If the status is SUCCESS: ONLY call Slack/Jira if you find a MAJOR HIDDEN ERROR.
    6. JIRA ASSIGNMENT: Use the specific JIRA Account ID for the assigned member when calling 'create_jira_issue'.

    RESPONSE FORMAT:
    Provide a JSON object with keys for tools to call, for example:
    {{
        "analysis": "Root cause / Hidden issue description",
        "category": "Frontend|Backend|DevOps",
        "tools": [
            {{"name": "send_slack_notification", "args": {{"message": "Reason...", "user_id": "MEMBER_SLACK_ID"}}}},
            {{"name": "update_tracking_sheet", "args": {{"task": "Fix...", "owner": "Member Name", "status": "Pending"}}}},
            {{"name": "create_jira_issue", "args": {{"summary": "Issue...", "description": "Context...", "assignee_id": "MEMBER_JIRA_ID"}}}}
        ]
    }}
    """

    try:
        if not model:
            print("Gemini model not initialized.")
            await emit_event(run_id, "ERROR", {"error": "Gemini model not initialized"})
            return

        # Run blocking Gemini call in a thread to avoid blocking the event loop
        response = await asyncio.to_thread(model.generate_content, prompt)
        content = response.text

        # Basic JSON extraction
        start = content.find('{')
        end = content.rfind('}') + 1
        decision = json.loads(content[start:end])

        print(f" Agent Decision: {decision.get('analysis')}")

        # ── Step: LLM Complete ──
        await emit_event(run_id, "LLM_COMPLETE", {"analysis": decision.get("analysis")})

        # Persistence: Save analysis
        analysis_path = os.path.join(ANALYSIS_DIR, f"{run_id}_analysis.json")
        with open(analysis_path, "w") as f:
            json.dump(decision, f, indent=4)

        # ── Step: Tools Planned ──
        planned_tools = [t["name"] for t in decision.get("tools", [])]
        await emit_event(run_id, "TOOLS_PLANNED", {"tools": planned_tools})

        # ── NEW: Approval Gate ──
        if planned_tools:
            await emit_event(run_id, "AWAITING_APPROVAL", {"message": "Waiting for manual approval via email."})
            # Send email in a thread to avoid blocking
            asyncio.create_task(asyncio.to_thread(send_approval_email, run_id, decision.get("analysis"), planned_tools))
            print(f" [Workflow] Paused for approval: {run_id}")
            return # Stop here and wait for /approve or /reject

        # ── Step: Completed (if no tools planned) ──
        await emit_event(run_id, "COMPLETED", {})

    except Exception as e:
        error_msg = f" Agent Error: {e}"
        print(error_msg)
        await emit_event(run_id, "ERROR", {"error": str(e)})
        with open(os.path.join(ANALYSIS_DIR, f"{run_id}_error.txt"), "w") as f:
            f.write(error_msg)


# ── Webhook Endpoint ───────────────────────────────

@app.post("/webhook")
async def handle_webhook(
    background_tasks: BackgroundTasks,
    status: str = Form(...),
    repo: str = Form(...),
    run_id: str = Form(...),
    branch: str = Form(...),
    commit: str = Form(None)
):
    # ── Step: Received ──
    print(f" Received webhook for {repo} (ID: {run_id}, Status: {status})")
    await emit_event(run_id, "RECEIVED", {
        "repo": repo, 
        "branch": branch, 
        "status": status,
        "message": "Webhook received. Server will poll GitHub for finalized logs."
    })

    # Trigger Agent in background (Non-blocking)
    # We pass logs_content=None to force the background task to poll GitHub for the "perfect" logs archive
    background_tasks.add_task(run_agent_workflow, status, repo, run_id, branch, None)

    return JSONResponse(
        status_code=202,
        content={
            "status": "accepted", 
            "message": "Webhook received. Agent analysis scheduled in background.",
            "run_id": run_id
        }
    )


@app.get("/api/approve/{run_id}")
async def approve_workflow(run_id: str, background_tasks: BackgroundTasks):
    wf = workflows.get(run_id)
    if not wf:
        return JSONResponse(status_code=404, content={"error": "Workflow not found"})
    
    if wf["current_step"] != "AWAITING_APPROVAL":
        return JSONResponse(status_code=400, content={"error": "Workflow is not awaiting approval"})

    background_tasks.add_task(execute_planned_tools, run_id)
    
    return HTMLResponse(content="""
    <html>
        <body style="font-family: sans-serif; text-align: center; padding: 50px;">
            <h1 style="color: #2e7d32;">✅ Approved!</h1>
            <p>The planned actions are now being executed in the background.</p>
            <p><a href="/dashboard">Return to Dashboard</a></p>
        </body>
    </html>
    """)


@app.get("/api/reject/{run_id}")
async def reject_workflow(run_id: str):
    wf = workflows.get(run_id)
    if not wf:
        return JSONResponse(status_code=404, content={"error": "Workflow not found"})
    
    await emit_event(run_id, "REJECTED", {"message": "User rejected actions."})
    
    return HTMLResponse(content="""
    <html>
        <body style="font-family: sans-serif; text-align: center; padding: 50px;">
            <h1 style="color: #d32f2f;">❌ Rejected</h1>
            <p>The planned actions have been cancelled.</p>
            <p><a href="/dashboard">Return to Dashboard</a></p>
        </body>
    </html>
    """)


@app.get("/health")
async def health():
    return {"status": "ok", "mcp_server": "active"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
