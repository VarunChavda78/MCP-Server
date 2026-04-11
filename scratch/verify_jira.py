from mcp_server import create_jira_issue
import os
from dotenv import load_dotenv

load_dotenv()

def test_jira():
    print("Testing JIRA Integration...")
    summary = "MCP TEST: Verification Issue"
    description = "This is a test issue created by the MCP DevOps Server to verify API connectivity."
    
    result = create_jira_issue(summary, description)
    print(f"Result: {result}")

if __name__ == "__main__":
    test_jira()
