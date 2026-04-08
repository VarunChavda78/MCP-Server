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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)