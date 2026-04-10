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
def create_jira_issue(summary: str, description: str) -> str:
    """
    Create a JIRA issue for tracking high-severity failures.
    """
    print(f"DEBUG: Placeholder for JIRA issue creation: {summary}")
    # In a real scenario, you'd use the jira-python library or requests.post to JIRA API
    return f"Successfully created JIRA issue: {summary} (Placeholder)"

if __name__ == "__main__":
    # Standard entry point for MCP stdio transport (useful for local debugging)
    mcp.run()
