import requests
from config import GITHUB_TOKEN

def fetch_workflow_logs(owner, repo, run_id):
    """Download logs of a GitHub Actions workflow run."""
    url = f"https://api.github.com/repos/{owner}/{repo}/actions/runs/{run_id}/logs"
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.text  # raw log content
    else:
        raise Exception(f"Failed to fetch logs: {response.status_code}")