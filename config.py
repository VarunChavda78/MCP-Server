import os
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")
GOOGLE_FORM_URL = os.getenv("GOOGLE_FORM_URL")
ENTRY_TASK = os.getenv("ENTRY_TASK")
ENTRY_OWNER = os.getenv("ENTRY_OWNER")
ENTRY_STATUS = os.getenv("ENTRY_STATUS")
JIRA_URL = os.getenv("JIRA_URL")
JIRA_EMAIL = os.getenv("JIRA_EMAIL")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")