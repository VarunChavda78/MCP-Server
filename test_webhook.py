import requests

test_payload = {
    "workflow_run": {
        "conclusion": "failure",
        "id": 1234567890,           # your real run ID
        "head_branch": "main"
    },
    "repository": {
        "full_name": "your_username/your_repo"
    },
    "sender": {
        "login": "dhruv"
    }
}

response = requests.post(
    "http://127.0.0.1:5000/webhook",
    json=test_payload,
    headers={"X-GitHub-Event": "workflow_run"}
)
print(response.status_code, response.json())