# utils/email_utils.py
from googleapiclient.discovery import build
from email.mime.text import MIMEText
import base64

def send_email(creds, to, subject, body):
    """
    Send an email using Gmail API.
    
    Args:
        creds: Google API credentials
        to: Recipient email address
        subject: Email subject
        body: Email body (HTML)
        
    Returns:
        Sent message
    """
    service = build('gmail', 'v1', credentials=creds)
    
    message = MIMEText(body, 'html')
    message['to'] = to
    message['subject'] = subject
    
    # Encode message
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
    
    try:
        sent_message = service.users().messages().send(
            userId='me',
            body={'raw': raw_message}
        ).execute()
        return sent_message
    except Exception as e:
        print(f"Error sending email: {e}")
        return None

def send_class_notification(creds, course_id, subject, message, include_meet_link=True):
    """
    Send a notification email to all students in a course.
    
    Args:
        creds: Google API credentials
        course_id: Google Classroom course ID
        subject: Email subject
        message: Email message
        include_meet_link: Whether to include the Google Meet link
        
    Returns:
        List of sent message IDs
    """
    # First, get all students in the course
    service = build('classroom', 'v1', credentials=creds)
    students = service.courses().students().list(courseId=course_id).execute()
    
    # Format HTML email
    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #1a73e8;">{subject}</h2>
        <div style="padding: 15px; background-color: #f8f9fa; border-radius: 8px;">
            <p>{message}</p>
        </div>
        <p style="color: #5f6368; font-size: 12px; margin-top: 20px;">
            This is an automated message from your Google Classroom course.
        </p>
    </div>
    """
    
    # Send to each student
    sent_messages = []
    for student in students.get('students', []):
        email = student.get('profile', {}).get('emailAddress')
        if email:
            sent = send_email(creds, email, subject, html_content)
            if sent:
                sent_messages.append(sent['id'])
    
    # Also post to Google Classroom
    from utils.google_classroom import post_announcement
    post_announcement(creds, course_id, message)
    
    return sent_messages