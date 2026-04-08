from flask import Flask, request, jsonify
from mcp_core import mcp_orchestrate

app = Flask(__name__)

@app.route("/webhook", methods=["POST"])
def github_webhook():
    event = request.headers.get("X-GitHub-Event")
    if event == "workflow_run":
        payload = request.json
        result = mcp_orchestrate(payload)
        return jsonify(result), 200
    else:
        return jsonify({"message": "ignored"}), 200
    
# NEW endpoint for your pipeline's direct notification
@app.route("/api/github-event", methods=["POST"])
def pipeline_event():
    data = request.json
    status = data.get("status")
    
    # Only trigger on failure
    if status != "failure":
        return jsonify({"status": "skipped", "reason": "workflow succeeded"}), 200
    
    # Construct a payload that mimics GitHub's workflow_run webhook
    # This allows reusing your existing mcp_orchestrate logic
    fake_payload = {
        "workflow_run": {
            "conclusion": status,           # "failure"
            "id": data.get("run_id"),
            "head_branch": data.get("branch")
        },
        "repository": {
            "full_name": data.get("repo")
        },
        "sender": {
            "login": data.get("actor", "unknown")
        }
    }
    
    # Call the same orchestration function
    result = mcp_orchestrate(fake_payload)
    return jsonify(result), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)