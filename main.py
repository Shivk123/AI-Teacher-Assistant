import streamlit as st
import json
import re
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
from PyPDF2 import PdfReader

def extract_json(text):
    try:
        text = re.sub(r"```json|```", "", text.strip())
        match = re.search(r"\[\s*{.*?}\s*]", text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        else:
            return None
    except json.JSONDecodeError as e:
        return f"JSON Parse Error: {str(e)}"

# --- Streamlit Setup ---
st.set_page_config(page_title="📚 AI Teacher Assistant", layout="wide")
st.title("📚 AI Teacher Assistant with Google Workspace")

creds = get_google_creds()

uploaded_file = st.file_uploader("Upload class notes / textbook (PDF)", type="pdf")
user_question = st.text_area("Ask a question from the notes", height=100)
action = st.selectbox("Choose Action", [
    "Summarize",
    "Generate Quiz",
    "Answer Question",
    "Create Assignment",
    "Schedule Meet",
    "Create Google Classroom"
])

if uploaded_file:
    document_text = extract_text(uploaded_file)
    st.write("Document Text Extracted:", document_text[:500])

    if st.button("Run"):
        if action == "Summarize":
            response = model(f"Summarize this content:{document_text[:3000]}")
            st.subheader("📄 Summary")
            st.write(response.text)

        elif action == "Generate Quiz":
            prompt = f"""
            Create 5 multiple-choice questions from this content. 
            Respond ONLY with valid JSON in this format (no explanation, no markdown):

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
            quiz_json = extract_json(response.text)
            
            if isinstance(quiz_json, str) and "JSON Parse Error" in quiz_json:
                st.error(quiz_json)
            elif quiz_json:
                st.json(quiz_json)
                form_url = create_quiz_form(creds, quiz_json)
                st.success("✅ Google Form Created")
                st.markdown(f"[Open Quiz Form]({form_url})")
            else:
                st.error("❌ Could not generate a valid quiz. Please check the document content or try again.")

        elif action == "Answer Question":
            prompt = f"Answer based on content: {document_text[:3000]} Question: {user_question}"
            response = model(prompt)
            st.subheader("💡 Answer")
            st.write(response.text)

        elif action == "Create Assignment":
            courses = list_courses(creds)
            course = st.selectbox("Choose Course", [f"{c['name']} ({c['id']})" for c in courses])
            course_id = course.split("(")[-1][:-1]
            create_assignment(creds, course_id, "AI Assignment", "Based on uploaded notes")
            st.success("Assignment Posted to Google Classroom")

        elif action == "Schedule Meet":
            meet_url = schedule_meet(creds, "Class Discussion", "2025-04-21T10:00:00Z", "2025-04-21T11:00:00Z")
            st.success("Meet Scheduled")
            st.markdown(f"[Join Meet]({meet_url})")

        elif action == "Create Google Classroom":
            st.subheader("📘 Create New Google Classroom Course")

            course_name = st.text_input("Course Name")
            section = st.text_input("Section", "")
            description = st.text_area("Course Description", "")
            room = st.text_input("Room Number (optional)", "")
            teacher_email = st.text_input("Teacher Email")
            student_email = st.text_input("Student Email")

            if st.button("Create Course"):
                course = create_course(creds, course_name, section, description, room)
                if course:
                    st.success(f"✅ Course '{course_name}' created with ID {course['id']}")
                    add_teacher(creds, course['id'], teacher_email)
                    add_student(creds, course['id'], student_email)
                    post_announcement(creds, course['id'], "🎉 Welcome to the course!")
                    st.info("Teacher and student added. Welcome announcement posted.")
                else:
                    st.error("❌ Failed to create course")
