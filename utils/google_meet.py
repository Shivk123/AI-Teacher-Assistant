# utils/google_meet.py
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import os
import time
from datetime import datetime, timedelta
import json
from google.oauth2.credentials import Credentials
from utils.ai_model import model

def get_meeting_recordings(creds, meeting_id):
    """
    Get recordings from a Google Meet session.
    
    Args:
        creds: Google API credentials
        meeting_id: ID of the Google Meet session
        
    Returns:
        List of recording metadata
    """
    # Note: This is a placeholder as the actual Meet API for recordings
    # requires enterprise workspace plan.
    # In a real implementation, you would use the Drive API to search for recordings
    
    service = build('drive', 'v3', credentials=creds)
    
    # Search for files with the meeting ID in the name
    results = service.files().list(
        q=f"name contains '{meeting_id}' and mimeType contains 'video/'",
        fields="files(id, name, webViewLink)"
    ).execute()
    
    return results.get('files', [])

def get_meeting_transcript(creds, recording_id):
    """
    Get a transcript from a Google Meet recording.
    
    Args:
        creds: Google API credentials
        recording_id: ID of the recording file
        
    Returns:
        Transcript text (or None if not available)
    """
    # This is a placeholder - in a real implementation, you would use
    # Google Cloud Speech-to-Text API or another transcription service
    
    # Simulate transcript fetching with a placeholder
    sample_transcript = f"This is a simulated transcript for meeting {recording_id}"
    return sample_transcript

def generate_meeting_summary(creds, meeting_id, course_id=None):
    """
    Generate a summary of a meeting using the recordings and AI.
    
    Args:
        creds: Google API credentials
        meeting_id: ID of the Google Meet session
        course_id: Optional course ID to post the summary
        
    Returns:
        Summary text
    """
    # Get recordings for the meeting
    recordings = get_meeting_recordings(creds, meeting_id)
    
    if not recordings:
        return "No recordings found for this meeting."
    
    # Get transcript for the first recording
    transcript = get_meeting_transcript(creds, recordings[0]['id'])
    
    # Use AI to generate summary
    prompt = f"""
    Generate a comprehensive summary of this class transcript.
    Include:
    1. Main topics covered
    2. Key points discussed
    3. Questions asked and answers provided
    4. Any assignments or homework mentioned
    5. Action items for students
    
    Transcript:
    {transcript[:3000]}  # Limit to first 3000 chars
    """
    
    response = model(prompt)
    summary = response.text
    
    # If course ID is provided, post the summary to Google Classroom
    if course_id:
        from utils.google_classroom import post_announcement
        
        announcement_text = f"""
        📝 Class Summary
        
        {summary}
        
        Recording link: {recordings[0].get('webViewLink', 'Not available')}
        """
        
        try:
            post_announcement(creds, course_id, announcement_text)
        except Exception as e:
            print(f"Failed to post summary: {e}")
    
    return summary

def schedule_automated_summary(creds, calendar_event_id, course_id, delay_minutes=10):
    """
    Schedule an automated summary to be generated after a meeting ends.
    
    Args:
        creds: Google API credentials
        calendar_event_id: Calendar event ID
        course_id: Course ID
        delay_minutes: Minutes to wait after meeting ends
        
    Returns:
        Boolean indicating success
    """
    # In a production app, you would use a task queue or scheduler
    # This is a simplified demonstration
    
    service = build('calendar', 'v3', credentials=creds)
    event = service.events().get(calendarId='primary', eventId=calendar_event_id).execute()
    
    # Get end time
    end_time = datetime.fromisoformat(event['end']['dateTime'].replace('Z', '+00:00'))
    
    # Calculate when to generate summary
    summary_time = end_time + timedelta(minutes=delay_minutes)
    
    # Store schedule info in a file (in a real app, use a database)
    schedule_data = {
        'event_id': calendar_event_id,
        'course_id': course_id,
        'summary_time': summary_time.isoformat(),
        'meet_id': event.get('conferenceData', {}).get('conferenceId', None)
    }
    
    # Save to schedule file
    with open('scheduled_summaries.json', 'a') as f:
        f.write(json.dumps(schedule_data) + '\n')
    
    return True