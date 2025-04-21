from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from datetime import datetime, timedelta
import time
from utils.google_calendar import schedule_meet
from utils.email_utils import send_class_notification
from utils.ai_model import model

def create_class_with_meet(creds, course_name, course_section, course_description, course_room, schedule):
    """
    Create a class with Google Meet integration.
    
    Args:
        creds: Google API credentials
        course_name: Name of the course
        course_section: Section of the course
        course_description: Description of the course
        course_room: Room number or location
        schedule: Dictionary containing schedule information
        
    Returns:
        Created course object
    """
    try:
        from utils.google_classroom import create_course
        from utils.google_calendar import schedule_recurring_classes
        
        # First create the course in Google Classroom
        course = create_course(
            creds, 
            course_name, 
            course_section, 
            course_description, 
            course_room
        )
        
        if not course:
            return None
            
        course_id = course['id']
        
        # Parse schedule information
        start_date = schedule.get('start_date')
        end_date = schedule.get('end_date')
        days = schedule.get('days', [])
        start_time_str = schedule.get('start_time')
        end_time_str = schedule.get('end_time')
        timezone = schedule.get('timezone', 'UTC')
        
        # Convert time strings to datetime objects
        from datetime import datetime, time
        
        # Parse start time
        if isinstance(start_time_str, str):
            hour, minute = map(int, start_time_str.split(':'))
            start_time = datetime.combine(start_date.date(), time(hour, minute))
        else:
            # Already a datetime or time object
            start_time = start_time_str if isinstance(start_time_str, datetime) else datetime.combine(start_date.date(), start_time_str)
            
        # Parse end time
        if isinstance(end_time_str, str):
            hour, minute = map(int, end_time_str.split(':'))
            end_time = datetime.combine(start_date.date(), time(hour, minute))
        else:
            # Already a datetime or time object
            end_time = end_time_str if isinstance(end_time_str, datetime) else datetime.combine(start_date.date(), end_time_str)
        
        # Schedule recurring classes
        meet_link = schedule_recurring_classes(
            creds,
            course_id,
            course_name,
            start_time,
            end_time,
            days,
            end_date,
            timezone
        )
        
        # Update course with meet link if available
        if meet_link:
            course['meetLink'] = meet_link
            
        return course
    except Exception as e:
        print(f"Error creating class with meet: {str(e)}")
        return None

def automate_class_management(creds, course_id):
    """
    Automate class management tasks.
    
    Args:
        creds: Google API credentials
        course_id: Google Classroom course ID
        
    Returns:
        Boolean indicating success
    """
    try:
        from utils.google_classroom import post_announcement
        
        # Generate class summary using AI
        prompt = f"""
        Create a welcome message for a new class.
        Include information about expectations and how to participate.
        """
        
        welcome_message = model(prompt)
        
        # Post summary to classroom
        post_announcement(creds, course_id, welcome_message)
        
        return True
    except Exception as e:
        print(f"Error automating class management: {str(e)}")
        return False

def schedule_class_reminders(creds, course_id, meet_events):
    """
    Schedule automated reminders for class sessions.
    
    Args:
        creds: Google API credentials
        course_id: Google Classroom course ID
        meet_events: List of Google Calendar events for the class sessions
    """
    for event in meet_events:
        # Schedule reminder 15 minutes before class
        reminder_time = event['start']['dateTime'] - timedelta(minutes=15)
        
        # Create reminder message
        reminder_text = f"""
        Class Reminder: {event['summary']}
        Time: {event['start']['dateTime'].strftime('%I:%M %p')}
        Meet Link: {event.get('hangoutLink', 'Check calendar for details')}
        """
        
        # Schedule the reminder
        schedule_meet(creds, reminder_time, reminder_text)

def process_meeting_minutes(creds, course_id, meeting_id):
    """
    Generate and share meeting minutes after a class session.
    
    Args:
        creds: Google API credentials
        course_id: Google Classroom course ID
        meeting_id: Google Meet meeting ID
    """
    try:
        # Generate meeting summary using AI
        summary = model(f"Create a summary of the class session about {meeting_id}. Include key points covered and important discussions.")
        
        # Post summary as an announcement
        announcement_text = f"""
        Meeting Minutes for {datetime.now().strftime('%B %d, %Y')}:
        
        {summary}
        
        Please review and let me know if you have any questions!
        """
        
        post_announcement(creds, course_id, announcement_text)
        
        # Send email notification to all students
        service = build('classroom', 'v1', credentials=creds)
        students = service.courses().students().list(courseId=course_id).execute()
        
        for student in students.get('students', []):
            send_class_notification(
                creds,
                course_id,
                f"Meeting Minutes Available - {datetime.now().strftime('%B %d, %Y')}",
                announcement_text,
                student['profile']['emailAddress']
            )
            
    except Exception as e:
        print(f"Error processing meeting minutes: {str(e)}")

def automate_class_management(creds, course_id):
    """
    Start automated management for a course.
    
    Args:
        creds: Google API credentials
        course_id: Google Classroom course ID
    """
    while True:
        try:
            # Get upcoming classes
            upcoming_classes = get_course_schedule(creds, course_id)
            
            for class_event in upcoming_classes:
                current_time = datetime.now()
                class_start = datetime.fromisoformat(class_event['start']['dateTime'])
                class_end = datetime.fromisoformat(class_event['end']['dateTime'])
                
                # Check if class is about to start (within 15 minutes)
                if 0 <= (class_start - current_time).total_seconds() <= 900:
                    # Send reminder
                    reminder_text = f"""
                    Class is starting soon!
                    Time: {class_start.strftime('%I:%M %p')}
                    Meet Link: {class_event.get('hangoutLink', 'Check calendar for details')}
                    """
                    post_announcement(creds, course_id, reminder_text)
                
                # Check if class just ended
                elif -300 <= (class_end - current_time).total_seconds() <= 0:
                    # Process meeting minutes
                    process_meeting_minutes(creds, course_id, class_event.get('meetId'))
            
            # Sleep for 5 minutes before checking again
            time.sleep(300)
            
        except Exception as e:
            print(f"Error in class automation: {str(e)}")
            time.sleep(300)  # Sleep for 5 minutes before retrying 