from github_client import fetch_workflow_logs
from llm_analyzer import analyze_logs
from actions import update_google_sheet, send_slack_msg, create_jira_issue

# Optional: GitHub username → Slack user ID mapping
# You can store this in config.py or a separate JSON file
GITHUB_TO_SLACK_ID = {
    "dhruv": "U0AR2DE15JB",      # example
    "mananv": "U1234567890",
    # add more as needed
}

def get_slack_user_id(github_username):
    """Convert GitHub username to Slack user ID (if mapping exists)."""
    return GITHUB_TO_SLACK_ID.get(github_username, None)

def mcp_orchestrate(payload):
    """
    Main orchestration function.
    payload: GitHub webhook payload for workflow_run event
    """
    workflow_run = payload.get("workflow_run", {})
    if workflow_run.get("conclusion") != "failure":
        return {"status": "skipped", "reason": "not a failure"}

    # Extract repo info
    repo_full_name = payload["repository"]["full_name"]
    owner, repo = repo_full_name.split("/")
    run_id = workflow_run["id"]
    head_branch = workflow_run["head_branch"]
    actor = payload.get("sender", {}).get("login", "unknown")

    print(f"🚨 Failure detected on {repo_full_name}, run {run_id}")

    # Step 1: Fetch logs
    try:
        logs = fetch_workflow_logs(owner, repo, run_id)
        logs_variable = logs  # store in variable for LLM
    except Exception as e:
        logs_variable = f"Error fetching logs: {e}"
        return {"status": "error", "detail": str(e)}

    # Step 2: LLM analysis
    analysis = analyze_logs(logs_variable)
    root_cause = analysis.get("root_cause", "Unknown")
    suggestion = analysis.get("suggestion", "")
    severity = analysis.get("severity", "medium")

    # Step 3: Actions
    # 3.1 Update Google Sheet
    update_google_sheet(
        task_name=f"Fix: {root_cause[:50]}",
        owner=actor,
        status="Pending"
    )

    # 3.2 Slack notification (using bot token)
    slack_msg = f"*CI Failure* on `{head_branch}`\nRoot cause: {root_cause}\nSuggestion: {suggestion}"
    slack_user_id = get_slack_user_id(actor)  # convert GitHub user to Slack ID if possible
    send_slack_msg(slack_msg, user_id=slack_user_id)

    # 3.3 Jira issue (only for high severity)
    if severity == "high":
        create_jira_issue(
            summary=f"[Auto] Pipeline failure on {repo}",
            description=f"Branch: {head_branch}\nRoot cause: {root_cause}\nSuggestion: {suggestion}"
        )

    # Return analysis for logging
    return {
        "status": "processed",
        "run_id": run_id,
        "analysis": analysis,
        "logs_preview": logs_variable[:500]
    }