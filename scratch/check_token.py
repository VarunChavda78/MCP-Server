import requests
from config import GITHUB_TOKEN

def check_token():
    url = "https://api.github.com/user"
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        user = response.json()
        print(f"✅ Token is valid. Authenticated as: {user['login']}")
    else:
        print(f"❌ Token is invalid or expired. Status: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    check_token()
