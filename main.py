import streamlit as st
import os
import json
from utils.google_auth import get_google_creds
from utils.pdf_utils import extract_text
from utils.ai_model import model, generate_quiz_json
from utils.google_classroom import (
    list_courses,
    create_assignment,
    create_course,
    add_teacher,
    add_student,
    post_announcement
)
from utils.google_calendar import schedule_meet
from utils.google_forms import create_quiz_form

# --- Streamlit Setup ---
st.set_page_config(page_title="📚 AI Teacher Assistant", layout="wide")

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
    
    tabs = ["Document Analysis", "Google Classroom", "Calendar & Meetings"]
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

# --- Document Analysis Tab ---
if selected_tab == "Document Analysis":
    st.header("📝 Document Analysis")

    uploaded_file = st.file_uploader("Upload class notes / textbook (PDF)", type="pdf")
    
    if uploaded_file:
        document_text = extract_text(uploaded_file)
        st.success(f"✅ Document loaded: {uploaded_file.name}")
        
        with st.expander("Preview Document"):
            st.write(document_text[:500] + "...")
        
        analysis_type = st.selectbox(
            "What would you like to do with this document?", 
            ["Summarize", "Generate Quiz", "Answer Questions"]
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
                                form_url = create_quiz_form(creds, quiz_json)
                            st.success("✅ Google Form Created")
                            st.markdown(f"[Open Quiz Form]({form_url})")
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

# --- Google Classroom Tab ---
elif selected_tab == "Google Classroom":
    st.header("🏫 Google Classroom Management")
    
    if not creds:
        st.warning("⚠️ Google authentication required for this section.")
    else:
        classroom_action = st.selectbox(
            "What would you like to do?",
            ["View Courses", "Create Assignment", "Create New Course"]
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
                    
                    if st.button("Post Assignment") and assignment_title:
                        course_id = course.split("(")[-1][:-1]
                        with st.spinner("Creating assignment..."):
                            create_assignment(creds, course_id, assignment_title, assignment_desc)
                        st.success("✅ Assignment Posted to Google Classroom")
            except Exception as e:
                st.error(f"Error: {str(e)}")
        
        elif classroom_action == "Create New Course":
            with st.form("new_course_form"):
                course_name = st.text_input("Course Name")
                section = st.text_input("Section", "")
                description = st.text_area("Course Description", "")
                room = st.text_input("Room Number (optional)", "")
                teacher_email = st.text_input("Additional Teacher Email (optional)")
                student_email = st.text_input("Student Email to Invite (optional)")
                
                submit_button = st.form_submit_button("Create Course")
                
            if submit_button and course_name:
                with st.spinner("Creating course..."):
                    course = create_course(creds, course_name, section, description, room)
                
                if course:
                    st.success(f"✅ Course '{course_name}' created with ID {course['id']}")
                    
                    if teacher_email:
                        add_teacher(creds, course['id'], teacher_email)
                        st.info(f"Teacher {teacher_email} added")
                    
                    if student_email:
                        add_student(creds, course['id'], student_email)
                        st.info(f"Student {student_email} invited")
                    
                    post_announcement(creds, course['id'], "🎉 Welcome to the course!")
                    st.info("Welcome announcement posted.")
                else:
                    st.error("❌ Failed to create course")

# --- Calendar Tab ---
elif selected_tab == "Calendar & Meetings":
    st.header("📅 Schedule Classes & Meetings")
    
    if not creds:
        st.warning("⚠️ Google authentication required for this section.")
    else:
        with st.form("schedule_meeting"):
            meeting_title = st.text_input("Meeting Title")
            meeting_date = st.date_input("Date")
            start_time = st.time_input("Start Time")
            end_time = st.time_input("End Time")
            
            submit_button = st.form_submit_button("Schedule Google Meet")
        
        if submit_button and meeting_title:
            # Convert to ISO format
            start_datetime = f"{meeting_date}T{start_time}:00Z"
            end_datetime = f"{meeting_date}T{end_time}:00Z"
            
            with st.spinner("Scheduling meeting..."):
                try:
                    meet_url = schedule_meet(creds, meeting_title, start_datetime, end_datetime)
                    st.success("✅ Meet Scheduled")
                    st.markdown(f"[Join Google Meet]({meet_url})")
                except Exception as e:
                    st.error(f"Error scheduling meeting: {str(e)}")