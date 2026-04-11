import g4f
from g4f.client import Client

client = Client()
try:
    response = client.chat.completions.create(
        model="gpt-4o",
        provider=g4f.Provider.PuterJS,
        messages=[{"role": "user", "content": "Hello, identify the root cause of this failure. Log: unauthorized: incorrect username"}]
    )
    print(response.choices[0].message.content)
except Exception as e:
    print(f"Error: {e}")
