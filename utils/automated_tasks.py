# utils/automated_tasks.py
import threading
import time
import json
import os
from datetime import datetime, timedelta
import schedule
from utils.google_auth import get_google_creds
from utils.google_meet import generate_meeting_summary
from utils.email_utils import send_class_notification
from utils.google_calendar import get_upcoming_classes
from config import DEFAULT_REMINDER_MINUTES

class AutomationScheduler:
    def __init__(self):
        self.running = False
        self.thread = None
        self.scheduled_tasks = []
        self.load_scheduled_tasks()
    
    def load_scheduled_tasks(self):
        """Load tasks from storage"""
        # In a real app, use a database instead of files
        if os.path.exists('scheduled_tasks.json'):
            try:
                with open('scheduled_tasks.json', 'r') as f:
                    self.scheduled_tasks = json.load(f)
            except:
                self.scheduled_tasks = []
    
    def save_scheduled_tasks(self):
        """Save tasks to storage"""
        with open('scheduled_tasks.json', 'w') as f:
            json.dump(self.scheduled_tasks, f)
    
    def start(self):
        """Start the automation scheduler"""
        if self.running:
            return False
        
        self.running = True
        self.thread = threading.Thread(target=self._run_scheduler)
        self.thread.daemon = True
        self.thread.start()
        return True
    
    def stop(self):
        """Stop the automation scheduler"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
            self.thread = None
        return True
    
    def _run_scheduler(self):
        """Run the scheduler loop"""
        while self.running:
            # Check for upcoming class reminders
            self._check_class_reminders()
            
            # Check for scheduled summaries
            self._check_scheduled_summaries()
            
            # Sleep for a minute
            time.sleep(60)
    
    def _check_class_reminders(self):
        """Check for upcoming classes and send reminders"""
        try:
            creds = get_google_creds()
            now = datetime.utcnow()
            
            # Get upcoming classes
            upcoming = get_upcoming_classes(creds, limit=20, days=1)
            
            # Check which ones need reminders
            for cls in upcoming:
                # Calculate minutes until class starts
                time_until = (cls['start_time'] - now).total_seconds() / 60
                
                # If within reminder time but not too close
                if DEFAULT_REMINDER_MINUTES <= time_until <= DEFAULT_REMINDER_MINUTES + 2:
                    # Check if we've already sent a reminder
                    reminder_id = f"reminder_{cls['id']}"
                    if reminder_id not in [task['id'] for task in self.scheduled_tasks]:
                        # Send reminder
                        if cls['course_id']:
                            subject = f"Reminder: {cls['summary']} starts in {int(time_until)} minutes"
                            message = f"""
                            Your class {cls['summary']} starts soon!
                            
                            Start time: {cls['start_time'].strftime('%I:%M %p')}
                            
                            Meeting link: {cls.get('meet_link', 'Check your calendar for details')}
                            """
                            
                            send_class_notification(creds, cls['course_id'], subject, message)
                            
                            # Mark as sent
                            self.scheduled_tasks.append({
                                'id': reminder_id,
                                'type': 'reminder',
                                'sent_at': now.isoformat()
                            })
                            self.save_scheduled_tasks()
        except Exception as e:
            print(f"Error checking class reminders: {e}")
    
    def _check_scheduled_summaries(self):
        """Check for classes that have ended and generate summaries"""
        try:
            if os.path.exists('scheduled_summaries.json'):
                creds = get_google_creds()
                now = datetime.utcnow()
                
                # Process each line in the file
                with open('scheduled_summaries.json', 'r') as f:
                    lines = f.readlines()
                
                new_lines = []
                for line in lines:
                    try:
                        data = json.loads(line.strip())
                        summary_time = datetime.fromisoformat(data['summary_time'])
                        
                        # Check if it's time to generate the summary
                        if now >= summary_time:
                            # Generate and post summary
                            if data.get('meet_id') and data.get('course_id'):
                                generate_meeting_summary(creds, data['meet_id'], data['course_id'])
                        else:
                            # Keep this task for later
                            new_lines.append(line)
                    except Exception as e:
                        print(f"Error processing summary task: {e}")
                        # Keep problematic tasks for now
                        new_lines.append(line)
                
                # Rewrite the file with remaining tasks
                with open('scheduled_summaries.json', 'w') as f:
                    f.writelines(new_lines)
        except Exception as e:
            print(f"Error checking scheduled summaries: {e}")

# Global instance
automation_scheduler = AutomationScheduler()

def start_automation():
    """Start the automation scheduler"""
    return automation_scheduler.start()

def stop_automation():
    """Stop the automation scheduler"""
    return automation_scheduler.stop()

def is_automation_running():
    """Check if automation is running"""
    return automation_scheduler.running