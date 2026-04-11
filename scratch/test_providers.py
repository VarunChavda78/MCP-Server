import g4f
from g4f.client import Client

# Try to force a specific provider that might work
client = Client()

providers = [
    g4f.Provider.Blackbox,
    g4f.Provider.ChatGptEs,
    g4f.Provider.DuckDuckGo,
    g4f.Provider.Bing
]

for provider in providers:
    print(f"Testing provider: {provider.__name__}...")
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            provider=provider,
            messages=[{"role": "user", "content": "Hello, are you working?"}]
        )
        print(f"Result: {response.choices[0].message.content[:100]}...")
        break
    except Exception as e:
        print(f"Failed: {e}")
