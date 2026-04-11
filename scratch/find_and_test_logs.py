import requests
from config import GITHUB_TOKEN

def find_any_run():
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}
    # List repos for the user
    repos_url = "https://api.github.com/user/repos"
    repos_resp = requests.get(repos_url, headers=headers)
    if repos_resp.status_code != 200:
        print("Failed to list repos.")
        return

    repos = repos_resp.json()
    for repo in repos:
        owner = repo['owner']['login']
        name = repo['name']
        print(f"Checking {owner}/{name} for workflow runs...")
        
        runs_url = f"https://api.github.com/repos/{owner}/{name}/actions/runs"
        runs_resp = requests.get(runs_url, headers=headers)
        if runs_resp.status_code == 200:
            runs = runs_resp.json().get("workflow_runs", [])
            if runs:
                run_id = runs[0]["id"]
                print(f"Found Run ID {run_id} in {owner}/{name}. Attempting to fetch logs...")
                
                logs_url = f"https://api.github.com/repos/{owner}/{name}/actions/runs/{run_id}/logs"
                logs_resp = requests.get(logs_url, headers=headers)
                print(f"Status: {logs_resp.status_code}")
                if logs_resp.status_code in [200, 302]:
                    print("✅ Successfully confirmed! Log endpoint is reachable and returning data/redirect.")
                    return
                else:
                    print(f"❌ Failed to fetch logs: {logs_resp.status_code}")
    print("No workflow runs found in any accessible repository.")

if __name__ == "__main__":
    find_any_run()
