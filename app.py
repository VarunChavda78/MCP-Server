import os
import time
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import JSONResponse
from mcp_server import mcp
from llm_analyzer import analyze_logs
import g4f
from g4f.client import Client
import json
from github_client import fetch_workflow_logs

app = FastAPI(title="MCP DevOps Webhook")
client = Client()

# Directory for log persistence
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

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
    {logs_content[:4000]}
    
    As a DevOps Agent, you have access to the following MCP TOOLS:
    1. send_slack_notification(message, user_id=None)
    2. update_tracking_sheet(task, owner, status)
    3. create_jira_issue(summary, description)

    DECIDE:
    1. What is the root cause?
    2. Should we notify Slack? (Yes, always on failure)
    3. Should we update the sheet? (Yes, for tracking)
    4. Should we create a Jira issue? (Only if it's a critical infrastructure failure)

    RESPONSE FORMAT:
    Provide a JSON object with keys for tools to call, for example:
    {{
        "analysis": "Brief root cause",
        "tools": [
            {{"name": "send_slack_notification", "args": {{"message": "Analysis details..."}}}},
            {{"name": "update_tracking_sheet", "args": {{"task": "Fix...", "owner": "actor", "status": "Pending"}}}}
        ]
    }}
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4", # g4f will use a default provider
            messages=[{"role": "user", "content": prompt}]
        )
        content = response.choices[0].message.content
        # Basic JSON extraction (naive)
        start = content.find('{')
        end = content.rfind('}') + 1
        decision = json.loads(content[start:end])
        
        print(f" Agent Decision: {decision.get('analysis')}")

        # Execute Tools
        for tool_call in decision.get("tools", []):
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            
            print(f" Executing MCP Tool: {tool_name}")
            
            # Use the MCP server's internal dispatch or direct call for simplicity
            if tool_name == "send_slack_notification":
                from mcp_server import send_slack_notification
                send_slack_notification(**tool_args)
            elif tool_name == "update_tracking_sheet":
                from mcp_server import update_tracking_sheet
                update_tracking_sheet(**tool_args)
            elif tool_name == "create_jira_issue":
                from mcp_server import create_jira_issue
                create_jira_issue(**tool_args)

    except Exception as e:
        print(f" Agent Error: {e}")

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
