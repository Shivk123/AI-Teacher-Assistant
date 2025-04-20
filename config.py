# config.py
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# === Gemini AI ===
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# === Google OAuth ===
GOOGLE_CLIENT_SECRET_FILE = os.getenv("GOOGLE_CLIENT_SECRET_FILE", "credentials.json")
GOOGLE_API_SCOPES = [
    'https://www.googleapis.com/auth/classroom.coursework.students',
    'https://www.googleapis.com/auth/classroom.courses',
    'https://www.googleapis.com/auth/classroom.announcements',
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/forms.body',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/gmail.send',
]

# === App Settings ===
APP_TITLE = "AI Teacher Assistant"
APP_ICON = "📚"
DEFAULT_REMINDER_MINUTES = 15  # Minutes before class to send reminder