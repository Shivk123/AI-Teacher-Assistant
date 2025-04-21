import google.generativeai as genai
from typing import Dict, Any, List, Optional
import json
import os
from google.generativeai import types

# Initialize the genai client
genai.configure(api_key="AIzaSyAFXfpQOv9JUboLVPeYFxmRWrgSzoh82xI")  # Use os.environ for security

class AIModel:
    def __init__(self):
        """Initialize the AI model with basic configuration."""
        try:
            # Initialize the model.  Use a default, and store the client.
            self.client = genai.GenerativeModel('gemini-2.0-flash')
            self.embedding_model = genai.GenerativeModel('embedding-001') #separate embedding model

            # Initialize chat
            self.chat = self.client.start_chat(history=[])
        except Exception as e:
            print(f"Error initializing AI model: {e}")
            raise

    def __call__(self, prompt: str) -> str:
        """Generate text response for a prompt with chat history."""
        try:
            response = self.chat.send_message(prompt)
            return response.text
        except Exception as e:
            print(f"Error generating response: {e}")
            return "I'm sorry, I encountered an error while processing your request."

    def generate_structured(self, prompt: Dict[str, Any]) -> Dict[str, Any]:
        """Generate structured output based on a schema."""
        try:
            # Format the prompt for structured generation
            formatted_prompt = f"""
            Generate data according to this schema:
            {json.dumps(prompt['schema'], indent=2)}
            
            Instructions: {prompt['instruction']}
            
            Respond ONLY with valid JSON matching the schema.
            """
            
            response = self.client.generate_content(formatted_prompt)

            try:
                return json.loads(response.text)
            except json.JSONDecodeError:
                print("Error parsing JSON response")
                return {}
        except Exception as e:
            print(f"Error generating structured output: {e}")
            return {}

    def get_embedding(self, text: str) -> List[float]:
        """Generate embedding for text."""
        try:
            response = self.embedding_model.generate_content(text)
            return response.embedding
        except Exception as e:
            print(f"Error generating embedding: {e}")
            return []

    def reset_chat(self):
        """Reset the chat history."""
        try:
            self.chat = self.client.start_chat(history=[])
        except Exception as e:
            print(f"Error resetting chat: {e}")



# Create a singleton instance
model = AIModel()

# Convenience function for embeddings
def get_embedding(text: str) -> List[float]:
    return model.get_embedding(text)

def generate_quiz_json(raw_text):
    """
    Extract JSON quiz data from the model's response.
    """
    try:
        # Clean up the text and find JSON array
        text = raw_text.strip()
        start = text.find('[')
        end = text.rfind(']') + 1
        if start >= 0 and end > start:
            json_str = text[start:end]
            return json.loads(json_str)
        return []
    except Exception:
        return []
    
def generate_meeting_summary(transcript):
    """
    Generate a summary of a meeting/class session.
    """
    try:
        prompt = f"""
        Create a detailed summary of this class session transcript.
        Include key points, questions asked, and action items.
        
        Transcript:
        {transcript}
        """
        
        response = model(prompt)
        return response
    except Exception as e:
        print(f"Error generating meeting summary: {e}")
        return "Error generating summary."
