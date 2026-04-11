import json
import g4f
from g4f.client import Client
from github_client import fetch_workflow_logs

client = Client()

def run_test_analysis(repo="VarunChavda78/SSF", run_id="24249547807", branch="main"):
    print(f"Fetching logs for {repo}...")
    logs_content = fetch_workflow_logs("VarunChavda78", "SSF", run_id)
    
    status = "failure"
    prompt = f"""
    A CI/CD pipeline failed in repo '{repo}' on branch '{branch}'.
    
    LOGS:
    {logs_content}
    
    As a DevOps Agent, you have access to the following MCP TOOLS:
    1. send_slack_notification(message, user_id=None)
    2. update_tracking_sheet(task, owner, status)
    3. create_jira_issue(summary, description)

    DECIDE:
    1. What is the root cause?
    2. Should we notify Slack? (Yes, always on failure)
    3. Should we update the sheet? (Yes, for tracking)
    4. Should we create a Jira issue? (Only if it's a critical infrastructure failure)

    RESPONSE FORMAT:
    Provide a JSON object with keys for tools to call, for example:
    {{
        "analysis": "Brief root cause",
        "tools": [
            {{"name": "send_slack_notification", "args": {{"message": "Analysis details..."}}}},
            {{"name": "update_tracking_sheet", "args": {{"task": "Fix...", "owner": "actor", "status": "Pending"}}}}
        ]
    }}
    """

    print("Sending prompt to LLM (using BlackboxPro)...")
    try:
        # Explicitly using a provider that often works without .har
        response = client.chat.completions.create(
            model="gpt-4o",
            provider=g4f.Provider.BlackboxPro,
            messages=[{"role": "user", "content": prompt}]
        )
        content = response.choices[0].message.content
        
        print("\n--- LLM RAW OUTPUT ---")
        print(content)
        print("----------------------\n")

        # Save raw output
        with open("scratch/agent_decision_raw.txt", "w", encoding="utf-8") as f:
            f.write(content)
            
        # Try to parse JSON
        start = content.find('{')
        end = content.rfind('}') + 1
        if start != -1 and end != -1:
            decision = json.loads(content[start:end])
            print("Successfully parsed JSON decision.")
            print(json.dumps(decision, indent=4))
        else:
            print("Warning: Response content is not valid JSON.")
            
    except Exception as e:
        print(f"Error during analysis: {e}")

if __name__ == "__main__":
    run_test_analysis()
