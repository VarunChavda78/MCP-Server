import os
from mcp.server.fastmcp import FastMCP
from slack_sdk import WebClient
import requests
from config import (
    SLACK_BOT_TOKEN, SLACK_CHANNEL_ID,
    GOOGLE_FORM_URL, ENTRY_TASK, ENTRY_OWNER, ENTRY_STATUS,
    JIRA_URL, JIRA_EMAIL, JIRA_API_TOKEN
)

# Initialize FastMCP Server
mcp = FastMCP("DevOps-Action-Server")

@mcp.tool()
def send_slack_notification(message: str, user_id: str = None) -> str:
    """
    Send a message to the configured Slack channel.
    If user_id is provided, it will mention the user.
    """
    if not SLACK_BOT_TOKEN or not SLACK_CHANNEL_ID:
        return "Slack not configured."

    client = WebClient(token=SLACK_BOT_TOKEN)
    formatted_message = f"🚨 <@{user_id}> {message}" if user_id else f"🚨 {message}"

    try:
        response = client.chat_postMessage(channel=SLACK_CHANNEL_ID, text=formatted_message)
        return f"Slack message sent successfully (TS: {response['ts']})"
    except Exception as e:
        return f"Error sending Slack message: {e}"

@mcp.tool()
def update_tracking_sheet(task: str, owner: str, status: str) -> str:
    """
    Update the Google Tracking Sheet (via Google Form submission).
    """
    if not GOOGLE_FORM_URL:
        return "Google Form URL not configured."

    data = {
        ENTRY_TASK: task,
        ENTRY_OWNER: owner,
        ENTRY_STATUS: status
    }
    try:
        resp = requests.post(GOOGLE_FORM_URL, data=data)
        return f"Google Sheet updated (Status: {resp.status_code})"
    except Exception as e:
        return f"Error updating Google Sheet: {e}"

@mcp.tool()
def create_jira_issue(summary: str, description: str, assignee_id: str = None) -> str:
    """
    Create a JIRA issue for tracking high-severity failures.
    If assignee_id is provided, the issue will be assigned to that user.
    """
    from config import JIRA_URL, JIRA_EMAIL, JIRA_API_TOKEN, JIRA_PROJECT_KEY, JIRA_ISSUE_TYPE
    
    if not all([JIRA_URL, JIRA_EMAIL, JIRA_API_TOKEN, JIRA_PROJECT_KEY]):
        return "JIRA not fully configured. Missing URL, Email, Token, or Project Key."

    # Ensure URL is properly formatted
    base_url = JIRA_URL.split("/rest/api")[0].rstrip("/")
    api_url = f"{base_url}/rest/api/2/issue"

    auth = (JIRA_EMAIL, JIRA_API_TOKEN)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    payload = {
        "fields": {
            "project": {
                "key": JIRA_PROJECT_KEY
            },
            "summary": summary,
            "description": description,
            "issuetype": {
                "name": JIRA_ISSUE_TYPE
            }
        }
    }

    if assignee_id:
        payload["fields"]["assignee"] = {"id": assignee_id}

    try:
        resp = requests.post(api_url, json=payload, auth=auth, headers=headers)
        if resp.status_code == 201:
            issue_key = resp.json().get("key")
            return f"Successfully created JIRA issue: {issue_key}"
        else:
            return f"Error creating JIRA issue: {resp.status_code} - {resp.text}"
    except Exception as e:
        return f"Exception while reaching JIRA: {e}"

if __name__ == "__main__":
    # Standard entry point for MCP stdio transport (useful for local debugging)
    mcp.run()
