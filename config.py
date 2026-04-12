import os
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Slack bot
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_CHANNEL_ID = os.getenv("SLACK_CHANNEL_ID")
SLACK_USER_ID = os.getenv("SLACK_USER_ID")   # optional default

# Team Member IDs
SLACK_ID_VARUN = os.getenv("SLACK_ID_VARUN")
SLACK_ID_KHUSHI = os.getenv("SLACK_ID_KHUSHI")
SLACK_ID_MANAV = os.getenv("SLACK_ID_MANAV")

JIRA_USER_ID_VARUN = os.getenv("JIRA_USER_ID_VARUN")
JIRA_USER_ID_KHUSHI = os.getenv("JIRA_USER_ID_KHUSHI")
JIRA_USER_ID_MANAV = os.getenv("JIRA_USER_ID_MANAV")

# Google Sheet (via Form)
GOOGLE_FORM_URL = os.getenv("GOOGLE_FORM_URL")
ENTRY_TASK = os.getenv("ENTRY_TASK")
ENTRY_OWNER = os.getenv("ENTRY_OWNER")
ENTRY_STATUS = os.getenv("ENTRY_STATUS")

# Jira (optional)
JIRA_URL = os.getenv("JIRA_URL")
JIRA_EMAIL = os.getenv("JIRA_EMAIL")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
JIRA_PROJECT_KEY = os.getenv("JIRA_PROJECT_KEY")
JIRA_ISSUE_TYPE = os.getenv("JIRA_ISSUE_TYPE", "Bug")

# SMTP / Approval Workflow
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
APPROVER_EMAIL = os.getenv("APPROVER_EMAIL", JIRA_EMAIL)
BASE_URL = os.getenv("BASE_URL", "https://mcp.varunchavda.in").rstrip("/")