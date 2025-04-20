# utils/google_calendar.py
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import uuid
from config import DEFAULT_REMINDER_MINUTES

def schedule_meet(creds, summary, start_time, end_time, course_id=None):
    """
    Schedule a Google Meet session and add it to Google Calendar.
    
    Args:
        creds: Google API credentials
        summary: Event summary/title
        start_time: ISO format start time
        end_time: ISO format end time
        course_id: Optional Google Classroom course ID
        
    Returns:
        Google Meet link
    """
    service = build('calendar', 'v3', credentials=creds)
    
    # Generate a unique request ID
    request_id = f"meet-{uuid.uuid4().hex[:8]}"
    
    # Create event with conference data
    event = {
        'summary': summary,
        'start': {'dateTime': start_time, 'timeZone': 'UTC'},
        'end': {'dateTime': end_time, 'timeZone': 'UTC'},
        'conferenceData': {
            'createRequest': {
                'requestId': request_id,
                'conferenceSolutionKey': {'type': 'hangoutsMeet'}
            }
        },
        'reminders': {
            'useDefault': False,
            'overrides': [
                {'method': 'email', 'minutes': DEFAULT_REMINDER_MINUTES},
                {'method': 'popup', 'minutes': 10}
            ]
        }
    }
    
    # Add course ID as extended property if provided
    if course_id:
        event['extendedProperties'] = {
            'private': {
                'courseId': course_id
            }
        }
    
    # Create the event
    created_event = service.events().insert(
        calendarId='primary',
        body=event,
        conferenceDataVersion=1
    ).execute()
    
    # Schedule automated summary after class ends
    if course_id:
        from utils.google_meet import schedule_automated_summary
        schedule_automated_summary(creds, created_event['id'], course_id)
    
    return created_event.get('hangoutLink', '')

def get_upcoming_classes(creds, limit=10, days=30):
    """
    Get list of upcoming classes from Google Calendar.
    
    Args:
        creds: Google API credentials
        limit: Maximum number of events to return
        days: Number of days to look ahead
        
    Returns:
        List of class events
    """
    service = build('calendar', 'v3', credentials=creds)
    
    # Set time bounds
    now = datetime.utcnow()
    time_min = now.isoformat() + 'Z'  # 'Z' indicates UTC time
    time_max = (now + timedelta(days=days)).isoformat() + 'Z'
    
    # Get events
    events_result = service.events().list(
        calendarId='primary',
        timeMin=time_min,
        timeMax=time_max,
        maxResults=limit,
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    
    events = events_result.get('items', [])
    
    # Format the events
    formatted_events = []
    for event in events:
        # Skip events without start/end times
        if 'dateTime' not in event['start'] or 'dateTime' not in event['end']:
            continue
            
        start = datetime.fromisoformat(event['start']['dateTime'].replace('Z', '+00:00'))
        end = datetime.fromisoformat(event['end']['dateTime'].replace('Z', '+00:00'))
        
        # Extract course ID if available
        course_id = None
        if 'extendedProperties' in event and 'private' in event['extendedProperties']:
            course_id = event['extendedProperties']['private'].get('courseId')
        
        # Extract Google Meet link if available
        meet_link = None
        if 'conferenceData' in event and 'entryPoints' in event['conferenceData']:
            for entry_point in event['conferenceData']['entryPoints']:
                if entry_point.get('entryPointType') == 'video':
                    meet_link = entry_point.get('uri')
        
        formatted_events.append({
            'id': event['id'],
            'summary': event['summary'],
            'start_time': start,
            'end_time': end,
            'course_id': course_id,
            'meet_link': meet_link
        })
    
    return formatted_events

def schedule_recurring_classes(creds, title, start_date, end_date, days_of_week, 
                              start_time, duration_minutes, course_id=None):
    """
    Schedule a series of recurring classes.
    
    Args:
        creds: Google API credentials
        title: Class title
        start_date: First day of classes (date object)
        end_date: Last day of classes (date object)
        days_of_week: List of days (0=Monday, 6=Sunday)
        start_time: Time object for class start time
        duration_minutes: Length of class in minutes
        course_id: Google Classroom course ID
        
    Returns:
        List of created event IDs
    """
    # Map day names to integers (0=Monday, 6=Sunday)
    day_map = {
        'Monday': 0, 'Tuesday': 1, 'Wednesday': 2, 'Thursday': 3,
        'Friday': 4, 'Saturday': 5, 'Sunday': 6
    }
    
    # Convert string day names to integers
    day_indices = [day_map[day] for day in days_of_week if day in day_map]
    
    # Generate all dates between start and end
    current_date = start_date
    class_dates = []
    
    while current_date <= end_date:
        # Check if this day of the week is in our list
        if current_date.weekday() in day_indices:
            class_dates.append(current_date)
        current_date += timedelta(days=1)
    
    # Create events for each date
    created_events = []
    
    for date in class_dates:
        # Combine date and time
        start_datetime = datetime.combine(date, start_time)
        end_datetime = start_datetime + timedelta(minutes=duration_minutes)
        
        # Format for API
        start_str = start_datetime.isoformat()
        end_str = end_datetime.isoformat()
        
        # Schedule the meeting
        meet_link = schedule_meet(creds, title, start_str, end_str, course_id)
        
        created_events.append({
            'date': date.strftime('%Y-%m-%d'),
            'start_time': start_time.strftime('%H:%M'),
            'meet_link': meet_link
        })
    
    return created_events