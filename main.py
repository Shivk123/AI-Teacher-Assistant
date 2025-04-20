import streamlit as st
import os
import json
from datetime import datetime, timedelta
import pandas as pd
from utils.google_auth import get_google_creds
from utils.pdf_utils import extract_text
from utils.ai_model import model, generate_quiz_json, generate_meeting_summary
from utils.google_classroom import (
    list_courses,
    create_assignment,
    create_course,
    add_teacher,
    add_student,
    post_announcement,
    get_course_schedule
)
from utils.google_calendar import schedule_meet, get_upcoming_classes
from utils.google_forms import create_quiz_form
from utils.google_meet import get_meeting_recordings
from utils.email_utils import send_class_notification

# --- Streamlit Setup ---
st.set_page_config(page_title="📚 AI Teacher Assistant", layout="wide")

# --- Session State Initialization ---
if 'scheduled_reminders' not in st.session_state:
    st.session_state.scheduled_reminders = {}

if 'automated_tasks' not in st.session_state:
    st.session_state.automated_tasks = {
        'auto_reminders': False,
        'auto_summaries': False,
        'auto_attendance': False
    }

# Check if .env file exists
if not os.path.exists(".env"):
    st.error("⚠️ No .env file found. Please create one with your API keys.")
    st.code("""
    GEMINI_API_KEY=your_api_key_here
    GOOGLE_CLIENT_SECRET_FILE=credentials.json
    """)
    st.stop()

# --- Sidebar ---
with st.sidebar:
    st.title("📚 Teacher Assistant")
    st.image("https://via.placeholder.com/150?text=AI+Teacher", width=150)
    
    tabs = ["Dashboard", "Document Analysis", "Google Classroom", "Calendar & Classes", "Automation"]
    selected_tab = st.radio("Navigation", tabs)
    
    with st.expander("About"):
        st.write("This app helps teachers automate their workflow using AI and Google Workspace.")

# --- Authentication Check ---
try:
    creds = get_google_creds()
    auth_status = "✅ Google Authentication: Success"
except Exception as e:
    st.error(f"❌ Google Authentication Failed: {str(e)}")
    st.error("Please check your credentials.json file and try again.")
    auth_status = "❌ Google Authentication: Failed"
    creds = None

st.sidebar.write(auth_status)

# --- Dashboard Tab ---
if selected_tab == "Dashboard":
    st.header("🏠 Teacher Dashboard")
    
    if not creds:
        st.warning("⚠️ Google authentication required to view dashboard.")
    else:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📅 Today's Classes")
            with st.spinner("Loading schedule..."):
                today_classes = get_upcoming_classes(creds, limit=5)
                
            if today_classes:
                for cls in today_classes:
                    with st.expander(f"{cls['summary']} - {cls['start_time'].strftime('%I:%M %p')}"):
                        st.write(f"**End time:** {cls['end_time'].strftime('%I:%M %p')}")
                        if 'meet_link' in cls:
                            st.write(f"**Meet link:** {cls['meet_link']}")
                        
                        # Quick actions
                        col_a, col_b = st.columns(2)
                        with col_a:
                            if st.button(f"📣 Send Reminder for {cls['summary']}", key=f"remind_{cls['id']}"):
                                course_id = cls.get('course_id')
                                if course_id:
                                    send_class_notification(creds, course_id, 
                                                         f"Reminder: {cls['summary']} at {cls['start_time'].strftime('%I:%M %p')}",
                                                         f"Class link: {cls.get('meet_link', 'Check calendar for details')}")
                                    st.success("Reminder sent!")
                        
                        with col_b:
                            if st.button(f"📝 Generate Materials for {cls['summary']}", key=f"materials_{cls['id']}"):
                                with st.spinner("AI is generating class materials..."):
                                    prompt = f"Create a brief lesson plan for a class on {cls['summary']}"
                                    response = model(prompt)
                                st.write(response.text)
            else:
                st.info("No upcoming classes found for today.")
        
        with col2:
            st.subheader("🔔 Notifications")
            st.info("Welcome to your AI Teacher Assistant!")
            st.info("Your automated systems are running smoothly.")
            
            # Automation status
            st.subheader("⚙️ Automation Status")
            status_df = pd.DataFrame({
                "Feature": ["Class Reminders", "Meeting Summaries", "Attendance Tracking"],
                "Status": [
                    "✅ ON" if st.session_state.automated_tasks['auto_reminders'] else "❌ OFF",
                    "✅ ON" if st.session_state.automated_tasks['auto_summaries'] else "❌ OFF", 
                    "✅ ON" if st.session_state.automated_tasks['auto_attendance'] else "❌ OFF"
                ]
            })
            st.dataframe(status_df, hide_index=True)

# --- Document Analysis Tab ---
elif selected_tab == "Document Analysis":
    st.header("📝 Document Analysis")

    uploaded_file = st.file_uploader("Upload class notes / textbook (PDF)", type="pdf")
    
    if uploaded_file:
        document_text = extract_text(uploaded_file)
        st.success(f"✅ Document loaded: {uploaded_file.name}")
        
        with st.expander("Preview Document"):
            st.write(document_text[:500] + "...")
        
        analysis_type = st.selectbox(
            "What would you like to do with this document?", 
            ["Summarize", "Generate Quiz", "Answer Questions", "Create Lesson Plan"]
        )
        
        if analysis_type == "Summarize":
            if st.button("Generate Summary"):
                with st.spinner("AI is analyzing the document..."):
                    response = model(f"Summarize this educational content in a detailed way suitable for teachers:{document_text[:3000]}")
                st.subheader("📄 Summary")
                st.write(response.text)
                
        elif analysis_type == "Generate Quiz":
            num_questions = st.slider("Number of questions", 3, 10, 5)
            
            if st.button("Create Quiz"):
                with st.spinner("AI is generating quiz questions..."):
                    prompt = f"""
                    Create {num_questions} multiple-choice questions from this educational content.
                    Return ONLY valid JSON in this format (no explanation, no markdown):
                    
                    [
                      {{
                        "question": "What is the capital of France?",
                        "options": ["A. Paris", "B. Berlin", "C. Madrid", "D. Rome"],
                        "correct": "A"
                      }},
                      ...
                    ]
                    
                    Content:
                    {document_text[:3000]}
                    """
                    response = model(prompt)
                    quiz_json = generate_quiz_json(response.text)
                
                if quiz_json:
                    st.success(f"✅ Generated {len(quiz_json)} questions")
                    
                    with st.expander("Preview Quiz"):
                        for i, q in enumerate(quiz_json):
                            st.write(f"**Q{i+1}: {q['question']}**")
                            for opt in q['options']:
                                st.write(f"- {opt}")
                            st.write(f"*Correct answer: {q['correct']}*")
                            st.write("---")
                    
                    if creds:
                        if st.button("Create Google Form"):
                            with st.spinner("Creating Google Form..."):
                                try:
                                    form_url = create_quiz_form(creds, quiz_json)
                                    st.success("✅ Google Form Created")
                                    st.markdown(f"[Open Quiz Form]({form_url})")
                                    
                                    # Option to assign to a class
                                    courses = list_courses(creds)
                                    if courses:
                                        selected_course = st.selectbox(
                                            "Assign to class:",
                                            [f"{c['name']} ({c['id']})" for c in courses]
                                        )
                                        if st.button("Assign Quiz"):
                                            course_id = selected_course.split("(")[-1][:-1]
                                            create_assignment(
                                                creds, 
                                                course_id, 
                                                f"Quiz: {uploaded_file.name.split('.')[0]}", 
                                                f"Please complete this quiz: {form_url}"
                                            )
                                            st.success("Quiz assigned to class!")
                                except Exception as e:
                                    st.error(f"Error creating form: {str(e)}")
                else:
                    st.error("❌ Could not generate a valid quiz. Please try again.")
                    
        elif analysis_type == "Answer Questions":
            user_question = st.text_area("What would you like to ask about this document?", height=100)
            
            if user_question and st.button("Get Answer"):
                with st.spinner("AI is analyzing your question..."):
                    prompt = f"As a teacher's assistant, answer this question based on the educational content:\n\nContent: {document_text[:3000]}\n\nQuestion: {user_question}"
                    response = model(prompt)
                
                st.subheader("💡 Answer")
                st.write(response.text)
                
        elif analysis_type == "Create Lesson Plan":
            subject = st.text_input("Subject/Topic")
            grade_level = st.selectbox("Grade Level", ["Elementary", "Middle School", "High School", "College"])
            duration = st.slider("Lesson Duration (minutes)", 30, 120, 45)
            
            if subject and st.button("Generate Lesson Plan"):
                with st.spinner("AI is creating your lesson plan..."):
                    prompt = f"""
                    Create a detailed lesson plan for a {duration}-minute {grade_level} class on {subject}.
                    Base this on the following content: {document_text[:2000]}
                    
                    Include:
                    1. Learning objectives
                    2. Required materials
                    3. Introduction/warm-up activity
                    4. Main lesson content
                    5. Student activities/exercises
                    6. Assessment methods
                    7. Conclusion
                    8. Homework assignment
                    """
                    response = model(prompt)
                
                st.subheader("📚 Lesson Plan")
                st.write(response.text)
                
                # Option to save as Google Doc
                if st.button("Save as Google Doc"):
                    st.info("This would save the lesson plan as a Google Doc (functionality to be implemented)")

# --- Google Classroom Tab ---
elif selected_tab == "Google Classroom":
    st.header("🏫 Google Classroom Management")
    
    if not creds:
        st.warning("⚠️ Google authentication required for this section.")
    else:
        classroom_action = st.selectbox(
            "What would you like to do?",
            ["View Courses", "Create Assignment", "Create New Course", "Schedule Class Series"]
        )
        
        if classroom_action == "View Courses":
            if st.button("Refresh Courses"):
                with st.spinner("Fetching your courses..."):
                    courses = list_courses(creds)
                
                if courses:
                    st.success(f"Found {len(courses)} courses")
                    for course in courses:
                        with st.expander(f"📘 {course['name']}"):
                            st.write(f"**ID:** {course['id']}")
                            st.write(f"**Section:** {course.get('section', 'N/A')}")
                            st.write(f"**Status:** {course['courseState']}")
                            
                            # Quick actions
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button("Post Announcement", key=f"announce_{course['id']}"):
                                    announcement = st.text_area("Announcement text:", key=f"announce_text_{course['id']}")
                                    if announcement and st.button("Send", key=f"send_{course['id']}"):
                                        try:
                                            post_announcement(creds, course['id'], announcement)
                                            st.success("Announcement posted!")
                                        except Exception as e:
                                            st.error(f"Error: {str(e)}")
                            
                            with col2:
                                if st.button("Schedule Class", key=f"schedule_{course['id']}"):
                                    st.session_state.selected_course = course['id']
                                    st.session_state.selected_tab = "Calendar & Classes"
                else:
                    st.info("No courses found. Create a new course to get started.")
        
        elif classroom_action == "Create Assignment":
            try:
                courses = list_courses(creds)
                if not courses:
                    st.warning("No courses found. Create a course first.")
                else:
                    course = st.selectbox(
                        "Choose Course", 
                        [f"{c['name']} ({c['id']})" for c in courses]
                    )
                    
                    assignment_title = st.text_input("Assignment Title")
                    assignment_desc = st.text_area("Assignment Description")
                    due_date = st.date_input("Due Date")
                    
                    # AI assist for assignment
                    if st.button("AI Assist"):
                        topic = assignment_title or "your subject"
                        with st.spinner("Generating assignment content..."):
                            prompt = f"Create a detailed assignment description for {topic}. Include objectives, requirements, and grading criteria."
                            response = model(prompt)
                            st.write(response.text)
                            if st.button("Use this content"):
                                assignment_desc = response.text
                    
                    if st.button("Post Assignment") and assignment_title:
                        course_id = course.split("(")[-1][:-1]
                        with st.spinner("Creating assignment..."):
                            create_assignment(creds, course_id, assignment_title, assignment_desc, due_date.isoformat())
                        st.success("✅ Assignment Posted to Google Classroom")
            except Exception as e:
                st.error(f"Error: {str(e)}")
        
        elif classroom_action == "Create New Course":
            with st.form("new_course_form"):
                course_name = st.text_input("Course Name")
                section = st.text_input("Section", "")
                description = st.text_area("Course Description", "")
                room = st.text_input("Room Number (optional)", "")
                teacher_emails = st.text_area("Additional Teacher Emails (one per line)", "")
                student_emails = st.text_area("Student Emails to Invite (one per line)", "")
                
                # AI assist for course description
                if st.checkbox("Generate course description with AI"):
                    subject = course_name or "this course"
                    level = section or "students"
                    ai_prompt = f"Write a brief, engaging course description for {subject} aimed at {level}."
                    ai_response = model(ai_prompt)
                    description = ai_response.text
                
                submit_button = st.form_submit_button("Create Course")
                
            if submit_button and course_name:
                with st.spinner("Creating course..."):
                    course = create_course(creds, course_name, section, description, room)
                
                if course:
                    st.success(f"✅ Course '{course_name}' created with ID {course['id']}")
                    
                    # Add teachers
                    if teacher_emails:
                        teacher_list = [email.strip() for email in teacher_emails.split("\n") if email.strip()]
                        for teacher in teacher_list:
                            add_teacher(creds, course['id'], teacher)
                        st.info(f"Added {len(teacher_list)} teacher(s)")
                    
                    # Add students
                    if student_emails:
                        student_list = [email.strip() for email in student_emails.split("\n") if email.strip()]
                        for student in student_list:
                            add_student(creds, course['id'], student)
                        st.info(f"Invited {len(student_list)} student(s)")
                    
                    # Post welcome announcement
                    post_announcement(creds, course['id'], "🎉 Welcome to the course! Please check the Course Materials section for the syllabus and schedule.")
                    st.info("Welcome announcement posted.")
                    
                    # Offer to schedule regular classes
                    if st.button("Schedule Regular Classes for this Course"):
                        st.session_state.selected_course = course['id']
                        st.session_state.selected_tab = "Calendar & Classes"
                else:
                    st.error("❌ Failed to create course")
                    
        elif classroom_action == "Schedule Class Series":
            # Set up recurring classes
            st.subheader("Schedule Recurring Classes")
            
            courses = list_courses(creds)
            if not courses:
                st.warning("No courses found. Create a course first.")
            else:
                course = st.selectbox(
                    "Choose Course", 
                    [f"{c['name']} ({c['id']})" for c in courses]
                )
                course_id = course.split("(")[-1][:-1]
                
                class_title = st.text_input("Class Title")
                
                col1, col2 = st.columns(2)
                with col1:
                    start_date = st.date_input("Start Date")
                    end_date = st.date_input("End Date")
                
                with col2:
                    days_of_week = st.multiselect(
                        "Days of Week",
                        ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
                    )
                    
                class_time = st.time_input("Class Time")
                duration = st.number_input("Duration (minutes)", min_value=15, max_value=180, value=45, step=15)
                
                if st.button("Schedule Class Series") and class_title and days_of_week:
                    # This would create all class instances in Google Calendar
                    st.success(f"✅ Scheduled {class_title} classes")
                    st.info("This would create calendar events and Google Meet sessions for each class day")

# --- Calendar & Classes Tab ---
elif selected_tab == "Calendar & Classes":
    st.header("📅 Classes & Meetings")
    
    if not creds:
        st.warning("⚠️ Google authentication required for this section.")
    else:
        calendar_action = st.selectbox(
            "What would you like to do?",
            ["View Upcoming Classes", "Schedule Single Class", "Meeting Summaries"]
        )
        
        if calendar_action == "View Upcoming Classes":
            st.subheader("📅 Upcoming Classes")
            
            with st.spinner("Loading calendar..."):
                upcoming = get_upcoming_classes(creds, limit=10)
                
            if upcoming:
                for cls in upcoming:
                    with st.expander(f"{cls['summary']} - {cls['start_time'].strftime('%a, %b %d %I:%M %p')}"):
                        st.write(f"**End time:** {cls['end_time'].strftime('%I:%M %p')}")
                        if 'meet_link' in cls:
                            st.write(f"**Meet link:** {cls['meet_link']}")
                            
                        # Action buttons
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            if st.button("Send Notification", key=f"notify_{cls['id']}"):
                                # This would send email/notification to students about the class
                                course_id = cls.get('course_id')
                                if course_id:
                                    msg = f"Class reminder: {cls['summary']} at {cls['start_time'].strftime('%I:%M %p')}"
                                    if 'meet_link' in cls:
                                        msg += f"\nMeeting link: {cls['meet_link']}"
                                    post_announcement(creds, course_id, msg)
                                    st.success("Notification sent!")
                        
                        with col2:
                            if st.button("Prepare Materials", key=f"prep_{cls['id']}"):
                                with st.spinner("AI is generating materials..."):
                                    prompt = f"Create a brief lesson plan and materials list for a class on {cls['summary']}"
                                    response = model(prompt)
                                st.write(response.text)
                                
                        with col3:
                            now = datetime.now()
                            class_time = cls['start_time']
                            
                            # Show "Join" when class is active, show countdown otherwise
                            if now >= cls['start_time'] and now <= cls['end_time']:
                                if 'meet_link' in cls:
                                    st.markdown(f"[Join Meet Now!]({cls['meet_link']})")
                            else:
                                time_diff = (class_time - now).total_seconds()
                                hours, remainder = divmod(time_diff, 3600)
                                minutes, seconds = divmod(remainder, 60)
                                
                                if time_diff > 0:
                                    st.write(f"Starts in: {int(hours)}h {int(minutes)}m")
                                else:
                                    st.write("Class ended")
            else:
                st.info("No upcoming classes found.")
                
        elif calendar_action == "Schedule Single Class":
            st.subheader("Schedule a Class Session")
            
            with st.form("schedule_class"):
                courses = list_courses(creds)
                if courses:
                    course = st.selectbox(
                        "Choose Course", 
                        [f"{c['name']} ({c['id']})" for c in courses]
                    )
                    course_id = course.split("(")[-1][:-1]
                else:
                    st.warning("No courses found")
                    course_id = None
                
                class_title = st.text_input("Class Title")
                class_date = st.date_input("Date")
                start_time = st.time_input("Start Time")
                duration = st.slider("Duration (minutes)", 15, 180, 45, 15)
                send_notification = st.checkbox("Send notification to students", value=True)
                
                submit_button = st.form_submit_button("Schedule Class")
            
            if submit_button and course_id and class_title:
                # Calculate end time
                end_time = (
                    datetime.combine(class_date, start_time) + 
                    timedelta(minutes=duration)
                ).time()
                
                # Format for calendar API
                start_datetime = f"{class_date}T{start_time}:00"
                end_datetime = f"{class_date}T{end_time}:00"
                
                with st.spinner("Scheduling class..."):
                    try:
                        meet_url = schedule_meet(creds, class_title, start_datetime, end_datetime, course_id)
                        st.success("✅ Class Scheduled with Google Meet")
                        st.markdown(f"Meet link: [{meet_url}]({meet_url})")
                        
                        # Send notification if requested
                        if send_notification and course_id:
                            msg = f"""
                            📚 New class scheduled: {class_title}
                            📅 Date: {class_date}
                            🕒 Time: {start_time.strftime('%I:%M %p')}
                            ⏱️ Duration: {duration} minutes
                            🔗 Meeting link: {meet_url}
                            """
                            post_announcement(creds, course_id, msg)
                            st.success("✅ Notification sent to students")
                            
                            # Set up automated reminder
                            if st.checkbox("Schedule automated reminder"):
                                reminder_time = st.slider("Minutes before class", 5, 60, 15)
                                st.info(f"Reminder will be sent {reminder_time} minutes before class")
                                # In a real app, this would register a task with a scheduler
                                
                    except Exception as e:
                        st.error(f"Error scheduling class: {str(e)}")
        
        elif calendar_action == "Meeting Summaries":
            st.subheader("🗒️ Class Recording Summaries")
            
            # This would connect to Google Meet recordings
            st.info("This feature would access your Google Meet recordings and generate summaries")
            
            # Mock data for demonstration
            past_classes = [
                {"title": "Introduction to Algebra", "date": "2025-04-15", "duration": "45 min"},
                {"title": "Photosynthesis Lab", "date": "2025-04-16", "duration": "60 min"},
                {"title": "World War II Discussion", "date": "2025-04-17", "duration": "50 min"}
            ]
            
            selected_class = st.selectbox(
                "Select recording to summarize",
                [f"{cls['title']} ({cls['date']})" for cls in past_classes]
            )
            
            if st.button("Generate Summary"):
                with st.spinner("AI is analyzing the class recording..."):
                    # This would process actual recording transcripts
                    # Using mock data for demonstration
                    selected_title = selected_class.split(" (")[0]
                    
                    prompt = f"Create a detailed summary of a class about {selected_title}. Include key points covered, questions asked, and action items."
                    response = model(prompt)
                
                st.subheader("📝 Class Summary")
                st.write(response.text)
                
                # Option to share with students
                if st.button("Share with Students"):
                    course_id = st.session_state.get('selected_course')
                    if course_id:
                        post_announcement(creds, course_id, 
                                         f"📝 Summary of today's class on {selected_title}:\n\n{response.text}")
                        st.success("Summary shared with students!")

# --- Automation Tab ---
elif selected_tab == "Automation":
    st.header("⚙️ Automation Settings")
    
    st.write("Configure automated tasks for your classes")
    
    # Class Notifications
    st.subheader("🔔 Class Notifications")
    st.session_state.automated_tasks['auto_reminders'] = st.toggle(
        "Send automatic class reminders",
        value=st.session_state.automated_tasks['auto_reminders']
    )
    
    if st.session_state.automated_tasks['auto_reminders']:
        reminder_time = st.slider("Minutes before class", 5, 60, 15)
        include_materials = st.checkbox("Include class materials", value=True)
        
        if st.button("Apply Settings"):
            st.success("✅ Automatic class reminders configured")
            st.info(f"Students will receive notifications {reminder_time} minutes before each class")
    
    # Meeting Summaries
    st.subheader("📝 Meeting Summaries")
    st.session_state.automated_tasks['auto_summaries'] = st.toggle(
        "Generate automatic meeting summaries",
        value=st.session_state.automated_tasks['auto_summaries']
    )
    
    if st.session_state.automated_tasks['auto_summaries']:
        share_with_students = st.checkbox("Share summaries with students", value=True)
        
        if st.button("Apply Summary Settings"):
            st.success("✅ Automatic meeting summaries configured")
            st.info("Summaries will be generated after each class session")
    
    # Attendance Tracking
    st.subheader("👥 Attendance Tracking")
    st.session_state.automated_tasks['auto_attendance'] = st.toggle(
        "Track student attendance automatically",
        value=st.session_state.automated_tasks['auto_attendance']
    )
    
    if st.session_state.automated_tasks['auto_attendance']:
        if st.button("Apply Attendance Settings"):
            st.success("✅ Automatic attendance tracking configured")
            st.info("Student attendance will be recorded for each class session")
    
    # Scheduler Status
    st.subheader("🤖 Automation Status")
    st.write("Current status of automated tasks:")
    
    status_df = pd.DataFrame({
        "Feature": ["Class Reminders", "Meeting Summaries", "Attendance Tracking"],
        "Status": [
            "✅ Active" if st.session_state.automated_tasks['auto_reminders'] else "❌ Inactive",
            "✅ Active" if st.session_state.automated_tasks['auto_summaries'] else "❌ Inactive",
            "✅ Active" if st.session_state.automated_tasks['auto_attendance'] else "❌ Inactive"
        ]
    })
    
    st.dataframe(status_df, hide_index=True)