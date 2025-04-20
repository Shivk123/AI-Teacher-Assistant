# utils/ai_model.py
from google import genai
import json
import re
import os
from config import GEMINI_API_KEY

# Check if API key is available
if not GEMINI_API_KEY:
    raise ValueError("Gemini API key not found. Please check your .env file.")

# Initialize the Gemini AI client
client = genai.Client(api_key=GEMINI_API_KEY)

def model(content, model_name='gemini-2.0-flash', max_retries=3):
    """
    Send a request to the Gemini AI model and return the response.
    
    Args:
        content: The prompt or question to send to the model
        model_name: The name of the Gemini model to use
        max_retries: Maximum number of retry attempts
        
    Returns:
        The model's response
    """
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=content)
            return response
        except Exception as e:
            if attempt == max_retries - 1:  # Last attempt
                raise Exception(f"Failed to get response from AI model after {max_retries} attempts: {str(e)}")
            continue  # Try again

def generate_quiz_json(raw_text):
    """
    Extract JSON quiz data from the model's response.
    
    Args:
        raw_text: The raw text response from the model
        
    Returns:
        List of quiz questions or empty list if parsing fails
    """
    try:
        # Clean up the text - remove markdown code blocks and find JSON array
        text = re.sub(r"```json|```", "", raw_text.strip())
        
        # Find anything that looks like a JSON array with objects inside
        match = re.search(r"\[[\s\S]*?\{[\s\S]*?\}[\s\S]*?\]", text)
        
        if match:
            json_str = match.group(0)
            parsed = json.loads(json_str)
            
            # Validate the structure
            for item in parsed:
                if not all(k in item for k in ["question", "options", "correct"]):
                    return []
            
            return parsed
        else:
            return []
    except Exception as e:
        print(f"Error parsing quiz JSON: {e}")
        return []