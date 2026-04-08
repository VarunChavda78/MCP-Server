import requests
from config import SLACK_WEBHOOK_URL, GOOGLE_FORM_URL, ENTRY_TASK, ENTRY_OWNER, ENTRY_STATUS

def update_google_sheet(task_name, owner, status):
    """Use Google Form to append a row."""
    data = {
        ENTRY_TASK: task_name,
        ENTRY_OWNER: owner,
        ENTRY_STATUS: status
    }
    try:
        resp = requests.post(GOOGLE_FORM_URL, data=data)
        print(f"Google Sheet update: {resp.status_code}")
    except Exception as e:
        print("Sheet error:", e)

def send_slack_message(message):
    if not SLACK_WEBHOOK_URL:
        return
    requests.post(SLACK_WEBHOOK_URL, json={"text": message})

def create_jira_issue(summary, description):
    """Optional – requires Jira API."""
    # Placeholder – implement if you have Jira
    print(f"Jira issue created: {summary}")
    # Example using requests with Basic Auth:
    # auth = (JIRA_EMAIL, JIRA_API_TOKEN)
    # payload = {"fields": {"project": {"key": "PROJ"}, "summary": summary, "description": description}}
    # requests.post(JIRA_URL, json=payload, auth=auth)