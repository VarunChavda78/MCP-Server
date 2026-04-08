import requests
from slack_sdk import WebClient
from config import (
    SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, SLACK_USER_ID,
    GOOGLE_FORM_URL, ENTRY_TASK, ENTRY_OWNER, ENTRY_STATUS
)

def send_slack_msg(message, user_id=None):
    """
    Send a Slack message using Bot Token.
    If user_id is provided, mention that user.
    """
    if not SLACK_BOT_TOKEN or not SLACK_CHANNEL_ID:
        print("⚠️ Slack not configured. Skipping.")
        return

    client = WebClient(token=SLACK_BOT_TOKEN)

    if user_id:
        formatted_message = f"🚨 <@{user_id}> here is the error:\n{message}"
    else:
        formatted_message = f"🚨 {message}"

    try:
        response = client.chat_postMessage(
            channel=SLACK_CHANNEL_ID,
            text=formatted_message
        )
        print(f"✅ Slack message sent: {response['ts']}")
    except Exception as e:
        print(f"❌ Slack error: {e}")

def update_google_sheet(task_name, owner, status):
    """Unchanged – uses your Google Form."""
    data = {
        ENTRY_TASK: task_name,
        ENTRY_OWNER: owner,
        ENTRY_STATUS: status
    }
    try:
        resp = requests.post(GOOGLE_FORM_URL, data=data)
        print(f"📝 Google Sheet update: {resp.status_code}")
    except Exception as e:
        print("❌ Sheet error:", e)

def create_jira_issue(summary, description):
    """Optional – unchanged."""
    print(f"📎 Jira issue (placeholder): {summary}")
    # Your Jira logic here...