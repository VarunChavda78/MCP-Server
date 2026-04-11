import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    print("Error: GOOGLE_API_KEY not found in .env")
    exit()

genai.configure(api_key=api_key)

models_to_test = [
    'gemini-1.5-flash',
    'gemini-flash-latest',
    'gemini-2.0-flash',
    'gemini-pro',
    'gemini-pro-latest'
]

for model_name in models_to_test:
    print(f"Testing model: {model_name}...")
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content("Hello! respond with 'SUCCESS'")
        print(f"Result {model_name}: {response.text}")
        print(f"--- WORKING MODEL FOUND: {model_name} ---")
        break
    except Exception as e:
        print(f"Failed {model_name}: {e}")
