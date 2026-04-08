import os
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("GITHUB_TOKEN")
OWNER = "your_github_username"    # change
REPO = "your_repo_name"           # change
RUN_ID = 1234567890               # your real run ID

url = f"https://api.github.com/repos/{OWNER}/{REPO}/actions/runs/{RUN_ID}/logs"
headers = {"Authorization": f"Bearer {TOKEN}"}

resp = requests.get(url, headers=headers)
print(f"Status: {resp.status_code}")
if resp.status_code == 200:
    print("✅ Logs fetched. First 500 chars:\n")
    print(resp.text[:500])
else:
    print("❌ Failed. Check token scope and run ID.")
    print(resp.text)