# utils/google_calendar.py
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import uuid
import pytz

# Default settings
DEFAULT_REMINDER_MINUTES = 15

def schedule_meet(creds, summary, start_time, end_time, course_id=None):
    """
    Schedule a Google Meet meeting and return the meet link.
    """
    try:
        # Build the Calendar API service
        service = build('calendar', 'v3', credentials=creds)
        
        # Create the event with Google Meet
        event = {
            'summary': summary,
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': 'UTC',
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': 'UTC',
            },
            'conferenceData': {
                'createRequest': {
                    'requestId': str(uuid.uuid4()),
                    'conferenceSolutionKey': {
                        'type': 'hangoutsMeet'
                    }
                }
            }
        }
        
        # Add the course ID as a description if provided
        if course_id:
            event['description'] = f"Course ID: {course_id}"
        
        # Insert the event
        event = service.events().insert(
            calendarId='primary',
            body=event,
            conferenceDataVersion=1
        ).execute()
        
        # Return the meet link
        return event.get('hangoutLink')
    except Exception as e:
        print(f"Error scheduling meet: {e}")
        return None

def get_upcoming_classes(creds, limit=5, days=1):
    """
    Get upcoming classes from Google Calendar.
    """
    try:
        service = build('calendar', 'v3', credentials=creds)
        now = datetime.now(pytz.UTC)
        end_time = now + timedelta(days=days)
        
        events_result = service.events().list(
            calendarId='primary',
            timeMin=now.isoformat(),
            timeMax=end_time.isoformat(),
            maxResults=limit,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        if not events:
            return []
            
        classes = []
        for event in events:
            start = datetime.fromisoformat(event['start']['dateTime'].replace('Z', '+00:00'))
            end = datetime.fromisoformat(event['end']['dateTime'].replace('Z', '+00:00'))
            
            class_info = {
                'id': event['id'],
                'summary': event['summary'],
                'start_time': start,
                'end_time': end,
                'meet_link': event.get('hangoutLink'),
                'course_id': None
            }
            
            # Extract course ID from description if present
            if 'description' in event:
                desc = event['description']
                if 'Course ID:' in desc:
                    class_info['course_id'] = desc.split('Course ID:')[1].strip()
            
            classes.append(class_info)
            
        return classes
    except Exception as e:
        print(f"Error getting upcoming classes: {e}")
        return []

def schedule_recurring_classes(creds, course_id, summary, start_time, end_time, 
                             days_of_week, end_date, timezone='UTC'):
    """
    Schedule recurring classes in Google Calendar.
    """
    try:
        service = build('calendar', 'v3', credentials=creds)
        
        # Convert days of week to RRULE format
        days_map = {
            'Monday': 'MO',
            'Tuesday': 'TU',
            'Wednesday': 'WE',
            'Thursday': 'TH',
            'Friday': 'FR',
            'Saturday': 'SA',
            'Sunday': 'SU'
        }
        
        rrule_days = [days_map[day] for day in days_of_week]
        
        # Create the recurring event
        event = {
            'summary': summary,
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': timezone,
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': timezone,
            },
            'recurrence': [
                f'RRULE:FREQ=WEEKLY;BYDAY={",".join(rrule_days)};UNTIL={end_date.strftime("%Y%m%dT%H%M%SZ")}'
            ],
            'description': f"Course ID: {course_id}",
            'conferenceData': {
                'createRequest': {
                    'requestId': str(uuid.uuid4()),
                    'conferenceSolutionKey': {
                        'type': 'hangoutsMeet'
                    }
                }
            }
        }
        
        # Insert the event
        event = service.events().insert(
            calendarId='primary',
            body=event,
            conferenceDataVersion=1
        ).execute()
        
        return event.get('hangoutLink')
    except Exception as e:
        print(f"Error scheduling recurring classes: {e}")
        return None