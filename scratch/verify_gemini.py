import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    print("Error: GOOGLE_API_KEY not found in .env")
    exit()

genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-2.0-flash')

try:
    response = model.generate_content("Hello! Respond with the word 'GEMINI_SUCCESS'.")
    print(f"Response: {response.text}")
    if "GEMINI_SUCCESS" in response.text:
        print("--- GEMINI API VERIFIED ---")
except Exception as e:
    print(f"Error calling Gemini: {e}")
