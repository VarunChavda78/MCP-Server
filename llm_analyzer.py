import g4f, re, ast
from g4f.client import Client

client = Client(provider=g4f.Provider.Chatai)

def analyze_logs(log_text):
    prompt = f"""
    Analyze the following CI/CD failure log.
    Return a Python dictionary with keys:
    - "root_cause": string
    - "suggestion": string
    - "severity": "low" | "medium" | "high"
    
    Logs:
    {log_text[:3000]}  # truncate to avoid token limits
    """

    try:
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a DevOps expert. Output ONLY valid Python dict."},
                {"role": "user", "content": prompt}
            ]
        )
        content = response.choices[0].message.content.strip()
        content = re.sub(r"```(?:python)?", "", content).replace("```", "").strip()
        # Parse dict
        result = ast.literal_eval(content)
        if isinstance(result, dict):
            return result
        else:
            return {"root_cause": "Unknown", "suggestion": "Check logs manually", "severity": "medium"}
    except Exception as e:
        print("LLM error:", e)
        return {"root_cause": "LLM failed", "suggestion": "Retry later", "severity": "medium"}