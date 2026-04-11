import requests
from config import GITHUB_TOKEN

OWNER = "VarunChavda78"
REPO = "MCP-Server"

def get_latest_run_id():
    url = f"https://api.github.com/repos/{OWNER}/{REPO}/actions/runs"
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        runs = response.json().get("workflow_runs", [])
        if runs:
            return runs[0]["id"]
    return None

def test_logs():
    run_id = get_latest_run_id()
    if not run_id:
        print("No recent workflow runs found.")
        return

    print(f"Testing logs for Run ID: {run_id}")
    url = f"https://api.github.com/repos/{OWNER}/{REPO}/actions/runs/{run_id}/logs"
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}
    response = requests.get(url, headers=headers)
    
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        print("✅ Success! Successfully retrieved logs.")
        # Logs are often a redirect to a zip file if fetched via this specific URL, 
        # but the API can sometimes return the raw text if configured differently 
        # or if using the interactive download URL.
        # Actually, the logs endpoint often returns a redirect to a temporary download URL.
        print(f"Response URL: {response.url}")
        if 'text' in response.headers.get('Content-Type', ''):
             print("Log Snippet:", response.text[:200])
        else:
             print("Log data is binary or redirected (likely a zip).")
    elif response.status_code == 302:
        print("✅ Success! Redirected to log download (302).")
        print(f"Redirect Location: {response.headers.get('Location')}")
    else:
        print(f"❌ Failed to fetch logs. Error: {response.text}")

if __name__ == "__main__":
    test_logs()
