# utils/automated_tasks.py
import threading
import time
import json
import os
from datetime import datetime, timedelta
import pytz
import schedule
from utils.google_auth import get_google_creds
from utils.email_utils import send_class_notification
from utils.google_calendar import get_upcoming_classes, DEFAULT_REMINDER_MINUTES
from utils.ai_model import model

# Default settings
DEFAULT_SUMMARY_DELAY = 10

class AutomationManager:
    def __init__(self):
        self.running = False
        self.thread = None
        self.creds = None
        self.reminder_minutes = DEFAULT_REMINDER_MINUTES
        self.summary_delay = DEFAULT_SUMMARY_DELAY

    def start(self):
        """Start the automation system."""
        if not self.running:
            self.running = True
            self.creds = get_google_creds()
            self.thread = threading.Thread(target=self._run_scheduler)
            self.thread.daemon = True
            self.thread.start()
            return True
        return False

    def stop(self):
        """Stop the automation system."""
        if self.running:
            self.running = False
            if self.thread:
                self.thread.join()
            return True
        return False

    def _run_scheduler(self):
        """Run the scheduler loop."""
        while self.running:
            schedule.run_pending()
            time.sleep(1)

    def schedule_reminders(self, minutes_before=DEFAULT_REMINDER_MINUTES):
        """Schedule class reminders."""
        self.reminder_minutes = minutes_before
        schedule.every().day.at("00:00").do(self._setup_daily_reminders)

    def schedule_summaries(self, delay_minutes=DEFAULT_SUMMARY_DELAY):
        """Schedule meeting summaries."""
        self.summary_delay = delay_minutes
        schedule.every().day.at("00:00").do(self._setup_daily_summaries)

    def _setup_daily_reminders(self):
        """Set up reminders for today's classes."""
        if not self.creds:
            self.creds = get_google_creds()
        
        upcoming = get_upcoming_classes(self.creds)
        for cls in upcoming:
            reminder_time = cls['start_time'] - timedelta(minutes=self.reminder_minutes)
            if reminder_time > datetime.now(pytz.UTC):
                schedule.every().day.at(reminder_time.strftime("%H:%M")).do(
                    self._send_reminder, cls
                )

    def _setup_daily_summaries(self):
        """Set up summaries for today's classes."""
        if not self.creds:
            self.creds = get_google_creds()
        
        upcoming = get_upcoming_classes(self.creds)
        for cls in upcoming:
            summary_time = cls['end_time'] + timedelta(minutes=self.summary_delay)
            if summary_time > datetime.now(pytz.UTC):
                schedule.every().day.at(summary_time.strftime("%H:%M")).do(
                    self._generate_summary, cls
                )

    def _send_reminder(self, class_info):
        """Send reminder for a class."""
        try:
            course_id = class_info.get('course_id')
            if course_id:
                msg = f"Reminder: {class_info['summary']} starts in {self.reminder_minutes} minutes"
                if 'meet_link' in class_info:
                    msg += f"\nMeeting link: {class_info['meet_link']}"
                send_class_notification(self.creds, course_id, "Class Reminder", msg)
        except Exception as e:
            print(f"Error sending reminder: {e}")

    def _generate_summary(self, class_info):
        """Generate summary for a class."""
        try:
            # Generate a basic summary using the AI model
            prompt = f"""
            Create a summary of the class session about {class_info['summary']}.
            Include key points covered and important discussions.
            """
            
            summary = model(prompt)
            
            # Share summary if course ID is available
            course_id = class_info.get('course_id')
            if course_id:
                send_class_notification(
                    self.creds,
                    course_id,
                    f"Summary: {class_info['summary']}",
                    summary
                )
        except Exception as e:
            print(f"Error generating summary: {e}")

# Create a singleton instance
automation_manager = AutomationManager()

def start_automation():
    """Start the automation system."""
    return automation_manager.start()

def stop_automation():
    """Stop the automation system."""
    return automation_manager.stop()

def is_automation_running():
    """Check if automation is running."""
    return automation_manager.running