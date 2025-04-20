from google import genai
from config import GEMINI_API_KEY
import json, re

client = genai.Client(api_key=GEMINI_API_KEY)

def model(cont):
    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents=cont)
    
    return response

def generate_quiz_json(raw_text):
    try:
        match = re.search(r'\[.*\]', raw_text, re.DOTALL)
        return json.loads(match.group(0)) if match else []
    except Exception as e:
        print(f"Error parsing quiz JSON: {e}")
        return []

