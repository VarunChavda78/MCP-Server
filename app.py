import os
import time
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import JSONResponse
from mcp_server import mcp
import google.generativeai as genai
import json
from github_client import fetch_workflow_logs
from config import GOOGLE_API_KEY, SLACK_ID_VARUN, SLACK_ID_KHUSHI, SLACK_ID_MANAV

app = FastAPI(title="MCP DevOps Webhook")

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

async def run_agent_workflow(status: str, repo: str, run_id: str, branch: str, logs_content: str):
    """
    The 'Brain' of the MCP Server. 
    Decides which tools to call based on the failure context.
    """
    if status != "failure":
        print(f"Skipping agent workflow for successful run: {run_id}")
        return

    print(f" Agent starting analysis for {repo} (Run: {run_id})")
    
    # 1. First, get the analysis from our specialized tool/logic
    # We can use the existing analyze_logs, but let's make it agentic
    prompt = f"""
    A CI/CD pipeline failed in repo '{repo}' on branch '{branch}'.
    
    LOGS:
    {logs_content[:]}
    
    TEAM MEMBERS:
    - Varun Chavda (DevOps): {SLACK_ID_VARUN}
    - Manav Thakkar (Frontend): {SLACK_ID_MANAV}
    - Khushi Patel (Backend): {SLACK_ID_KHUSHI}

    As a DevOps Agent, you have access to the following MCP TOOLS:
    1. send_slack_notification(message, user_id=None)
    2. update_tracking_sheet(task, owner, status)
    3. create_jira_issue(summary, description)

    DECIDE:
    1. What is the root cause?
    2. Categorize the error: DevOps, Frontend, or Backend.
    3. Assign the correct team member and use their SLACK ID:
       - DevOps -> Varun Chavda
       - Frontend -> Manav Thakkar
       - Backend -> Khushi Patel
    4. Should we notify Slack? (Yes, always on failure. Include the correct 'user_id' for @mention)
    5. Should we update the sheet? (Yes, use the assigned member's name as 'owner')
    6. Should we create a Jira issue? (YES, if it's a critical infrastructure failure like a credential error, docker daemon issue, or recurring environmental problem).

    RESPONSE FORMAT:
    Provide a JSON object with keys for tools to call, for example:
    {{
        "analysis": "Brief root cause and category",
        "tools": [
            {{"name": "send_slack_notification", "args": {{"message": "Analysis details...", "user_id": "MEMBER_ID"}}}},
            {{"name": "update_tracking_sheet", "args": {{"task": "Fix...", "owner": "Member Name", "status": "Pending"}}}},
            {{"name": "create_jira_issue", "args": {{"summary": "Critical failure in...", "description": "Full log context..."}}}}
        ]
    }}
    """

    try:
        if not model:
            print("❌ Gemini model not initialized.")
            return

        response = model.generate_content(prompt)
        content = response.text
        
        # Basic JSON extraction (naive)
        start = content.find('{')
        end = content.rfind('}') + 1
        decision = json.loads(content[start:end])
        
        print(f" Agent Decision: {decision.get('analysis')}")

        # Persistence: Save analysis
        analysis_path = os.path.join(ANALYSIS_DIR, f"{run_id}_analysis.json")
        with open(analysis_path, "w") as f:
            json.dump(decision, f, indent=4)

        # Execute Tools
        for tool_call in decision.get("tools", []):
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            
            print(f" Executing MCP Tool: {tool_name}")
            
            # Use the MCP server's internal dispatch or direct call for simplicity
            if tool_name == "create_jira_issue":
                from mcp_server import create_jira_issue
                create_jira_issue(**tool_args)
            elif tool_name == "send_slack_notification":
                from mcp_server import send_slack_notification
                send_slack_notification(**tool_args)
            elif tool_name == "update_tracking_sheet":
                from mcp_server import update_tracking_sheet
                update_tracking_sheet(**tool_args)

    except Exception as e:
        error_msg = f" Agent Error: {e}"
        print(error_msg)
        with open(os.path.join(ANALYSIS_DIR, f"{run_id}_error.txt"), "w") as f:
            f.write(error_msg)

@app.post("/webhook")
async def handle_webhook(
    background_tasks: BackgroundTasks,
    status: str = Form(...),
    repo: str = Form(...),
    run_id: str = Form(...),
    branch: str = Form(...),
    commit: str = Form(None)
):
    # 0. Fetch logs from GitHub API
    try:
        if "/" not in repo:
            owner = "VarunChavda78" # Default to user if repo name is provided without owner
            repo_name = repo
        else:
            owner, repo_name = repo.split("/", 1)
            
        print(f" Fetching logs from GitHub: {owner}/{repo_name} (Run ID: {run_id})")
        logs_text = fetch_workflow_logs(owner, repo_name, run_id)
        
    except Exception as e:
        print(f" Failed to fetch logs from GitHub: {e}")
        return JSONResponse(
            status_code=400, 
            content={"status": "error", "message": f"Could not fetch logs: {str(e)}"}
        )

    # 1. Save logs to disk (Persistence)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"{run_id}_{status}_{timestamp}.log"
    log_path = os.path.join(LOG_DIR, log_filename)
    
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(logs_text)
    
    print(f" Received webhook for {repo}. Status: {status}. Logs saved to {log_path}")

    # 2. Trigger Agent in background (Non-blocking)
    background_tasks.add_task(run_agent_workflow, status, repo, run_id, branch, logs_text)

    return {"status": "accepted", "log_file": log_filename}

@app.get("/health")
async def health():
    return {"status": "ok", "mcp_server": "active"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
