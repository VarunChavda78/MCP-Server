import requests
import zipfile
import io
from config import GITHUB_TOKEN

def fetch_workflow_logs(owner, repo, run_id):
    """Download and unzip logs of a GitHub Actions workflow run."""
    url = f"https://api.github.com/repos/{owner}/{repo}/actions/runs/{run_id}/logs"
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        try:
            # The GitHub API returns logs as a zip file
            with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                all_logs = []
                # namelist() gives all files in the zip
                for filename in sorted(z.namelist()):
                    # Workflows logs are typically in .txt files
                    if filename.endswith(".txt"):
                        with z.open(filename) as f:
                            content = f.read().decode("utf-8", errors="ignore")
                            all_logs.append(f"--- FILE: {filename} ---\n{content}\n")
                
                if not all_logs:
                    return "No log files found in the archive."
                    
                return "\n".join(all_logs)
        except zipfile.BadZipFile:
            # Fallback for unexpected response format
            return response.text
    else:
        raise Exception(f"Failed to fetch logs: {response.status_code}")


def get_workflow_run_status(owner, repo, run_id):
    """Check the status and conclusion of a workflow run."""
    url = f"https://api.github.com/repos/{owner}/{repo}/actions/runs/{run_id}"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        return data.get("status"), data.get("conclusion")
    else:
        raise Exception(f"Failed to fetch run status: {response.status_code}")