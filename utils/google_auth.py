import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from config import GOOGLE_CLIENT_SECRET_FILE, GOOGLE_API_SCOPES

TOKEN_PATH = "token.pkl"

def get_google_creds():
    creds = None

    # Load previously saved credentials
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, 'rb') as token:
            creds = pickle.load(token)

    # If no valid creds, run flow and save
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(GOOGLE_CLIENT_SECRET_FILE, GOOGLE_API_SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save for next time
        with open(TOKEN_PATH, 'wb') as token:
            pickle.dump(creds, token)

    return creds
