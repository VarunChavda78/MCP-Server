import requests
from config import GITHUB_TOKEN

def find_recent_run():
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}
    repos_url = "https://api.github.com/user/repos?sort=updated"
    repos_resp = requests.get(repos_url, headers=headers)
    if repos_resp.status_code != 200:
        print("Failed to list repos.")
        return

    repos = repos_resp.json()
    for repo in repos:
        owner = repo['owner']['login']
        name = repo['name']
        
        runs_url = f"https://api.github.com/repos/{owner}/{name}/actions/runs"
        runs_resp = requests.get(runs_url, headers=headers)
        if runs_resp.status_code == 200:
            runs = runs_resp.json().get("workflow_runs", [])
            for run in runs:
                run_id = run["id"]
                created_at = run["created_at"]
                
                logs_url = f"https://api.github.com/repos/{owner}/{name}/actions/runs/{run_id}/logs"
                logs_resp = requests.get(logs_url, headers=headers)
                
                if logs_resp.status_code in [200, 302]:
                    print(f"SUCCESS: Found active logs in {owner}/{name} (Run ID: {run_id}, Created: {created_at})")
                    print(f"Status: {logs_resp.status_code}")
                    return
                else:
                    # Just skip and keep looking if it's 410 or other
                    continue
    print("No recent workflow runs with active logs found.")

if __name__ == "__main__":
    find_recent_run()
