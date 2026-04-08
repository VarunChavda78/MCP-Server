import os
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# Slack bot
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_CHANNEL_ID = os.getenv("SLACK_CHANNEL_ID")
SLACK_USER_ID = os.getenv("SLACK_USER_ID")   # optional default

# Google Sheet (via Form)
GOOGLE_FORM_URL = os.getenv("GOOGLE_FORM_URL")
ENTRY_TASK = os.getenv("ENTRY_TASK")
ENTRY_OWNER = os.getenv("ENTRY_OWNER")
ENTRY_STATUS = os.getenv("ENTRY_STATUS")

# Jira (optional)
JIRA_URL = os.getenv("JIRA_URL")
JIRA_EMAIL = os.getenv("JIRA_EMAIL")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")