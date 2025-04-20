
from googleapiclient.discovery import build

def schedule_meet(creds, summary, start_time, end_time):
    service = build('calendar', 'v3', credentials=creds)
    event = {
        'summary': summary,
        'start': {'dateTime': start_time, 'timeZone': 'UTC'},
        'end': {'dateTime': end_time, 'timeZone': 'UTC'},
        'conferenceData': {'createRequest': {'requestId': 'meet123'}}
    }
    created_event = service.events().insert(calendarId='primary', body=event, conferenceDataVersion=1).execute()
    return created_event['hangoutLink']
