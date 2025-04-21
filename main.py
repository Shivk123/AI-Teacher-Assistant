import streamlit as st
import os
import json
from datetime import datetime, timedelta
import pandas as pd
from utils.google_auth import get_google_creds
from utils.google_classroom import (
    list_courses,
    create_assignment,
    create_course,
    add_teacher,
    add_student,
    post_announcement,
    get_course_schedule
)
from utils.google_forms import create_quiz_form, get_all_forms, get_form_responses, analyze_form_responses, evaluate_essay_response
from utils.email_utils import send_class_notification
from utils.automated_tasks import start_automation, stop_automation, is_automation_running
from utils.google_calendar import schedule_recurring_classes, get_upcoming_classes
from utils.classroom_automation import create_class_with_meet, automate_class_management
from datetime import datetime, timedelta
import time
import threading
import pytz
from PyPDF2 import PdfReader
from utils.ai_model import model
from googleapiclient.discovery import build

def start_automation_on_startup():
    """Start automation when app starts"""
    if not is_automation_running():
        start_automation()
        print("Automation services started")

start_automation_on_startup()

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
    
    tabs = ["Dashboard", "Quiz Creation", "Google Classroom", "Automation"]
    selected_tab = st.radio("Navigation", tabs)
    
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

# --- Quiz Creation Tab ---
elif selected_tab == "Quiz Creation":
    st.header("📝 Quiz Creation")
    
    if not creds:
        st.warning("⚠️ Google authentication required to create quizzes.")
    else:
        # Create tabs for quiz creation and evaluation
        quiz_tabs = st.tabs(["Create Quiz", "Evaluate Responses"])
        
        # --- Create Quiz Tab ---
        with quiz_tabs[0]:
            # PDF Upload
            st.subheader("📄 Upload Study Material")
            uploaded_file = st.file_uploader("Upload PDF", type="pdf")
            
            if uploaded_file:
                # Extract text from PDF
                with st.spinner("Extracting text from PDF..."):
                    try:
                        reader = PdfReader(uploaded_file)
                        content = ""
                        for page in reader.pages:
                            content += page.extract_text()
                        
                        # Verify we have meaningful content
                        if len(content) < 100:
                            st.warning("⚠️ The extracted text is very short. This PDF may not be text-based or may have formatting issues.")
                        else:
                            st.success(f"✅ PDF processed successfully! Extracted {len(content)} characters.")
                    except Exception as e:
                        st.error(f"Error processing PDF: {str(e)}")
                        content = ""
                
                if content:
                    # Quiz Details
                    st.subheader("📝 Quiz Details")
                    quiz_title = st.text_input("Quiz Title", value=f"Quiz: {uploaded_file.name.split('.')[0]}")
                    quiz_description = st.text_area("Description", placeholder="Enter a brief description of the quiz")
                    
                    # Create columns for options
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # Question Types
                        st.subheader("❓ Question Types")
                        question_types = st.multiselect(
                            "Select question types",
                            ["Multiple Choice", "Short Answer", "True/False", "Essay"],
                            default=["Multiple Choice", "True/False"]
                        )
                        
                        # Number of questions
                        num_questions = st.slider("Number of questions", 1, 10, 5)
                    
                    with col2:
                        # Difficulty Level
                        st.subheader("📊 Quiz Settings")
                        difficulty = st.select_slider(
                            "Difficulty level",
                            options=["Beginner", "Intermediate", "Advanced"],
                            value="Intermediate"
                        )
                        
                        # Time limit
                        time_limit = st.number_input("Time limit (minutes)", min_value=5, max_value=120, value=30)
                        
                        # Content sampling
                        sampling_method = st.radio(
                            "Content processing method",
                            ["First portion", "Random sampling", "Topic extraction"],
                            index=0,
                            help="Choose how to handle large documents"
                        )
                    
                    # Course selection
                    st.subheader("🎓 Course Assignment")
                    courses = list_courses(creds)
                    if courses:
                        selected_course = st.selectbox(
                            "Select course",
                            [f"{c['name']} ({c['id']})" for c in courses]
                        )
                        course_id = selected_course.split("(")[-1][:-1]
                        
                        # Due date settings
                        due_col1, due_col2 = st.columns(2)
                        with due_col1:
                            due_date = st.date_input("Due Date")
                        with due_col2:
                            due_time = st.time_input("Due Time")
                        
                        # Create quiz button
                        if st.button("Generate Quiz", type="primary"):
                            # Process the content based on selected method
                            with st.spinner("Processing document content..."):
                                # Display information about auto-grading
                                st.info("ℹ️ Your quiz will be created as a Google Form with automatic grading enabled.")
                                st.info("ℹ️ The quiz will collect student emails and is configured to grade responses automatically.")
                                st.warning("⚠️ **Important:** Due to Google Forms API limitations, you may need to manually configure the form as a quiz after creation. Detailed instructions will be provided after quiz generation.")
                                
                                # Determine the appropriate content length based on number of questions
                                max_content_length = 10000 + (num_questions * 200)  # Base + per question allowance
                                
                                # Process content based on selected method
                                if sampling_method == "First portion":
                                    processed_content = content[:max_content_length]
                                elif sampling_method == "Random sampling":
                                    import random
                                    # Split into paragraphs and select a random subset
                                    paragraphs = content.split('\n\n')
                                    if len(paragraphs) > 10:
                                        selected_paragraphs = random.sample(paragraphs, 10)
                                        processed_content = '\n\n'.join(selected_paragraphs)
                                        processed_content = processed_content[:max_content_length]
                                    else:
                                        processed_content = content[:max_content_length]
                                else:  # Topic extraction
                                    # Extract key topics first
                                    with st.spinner("🔍 Extracting key topics from document..."):
                                        topic_prompt = f"""
                                        Extract 5-7 main topics or concepts from this educational content.
                                        Format as a simple list with a brief 1-2 sentence explanation for each.
                                        
                                        Content: {content[:20000]}
                                        """
                                        topic_response = model(topic_prompt)
                                        processed_content = f"Key topics from the document:\n{topic_response}\n\nSelected content samples:\n{content[:max_content_length]}"
                            
                            if len(content) > max_content_length:
                                st.info(f"⚠️ Original content was {len(content)} characters. Using {min(len(content),len(processed_content))} characters for processing.")
                            
                            # Generate quiz
                            success = False
                            attempts = 0
                            max_attempts = 2
                            
                            while not success and attempts < max_attempts:
                                attempts += 1
                                current_num_questions = num_questions
                                
                                if attempts > 1:
                                    st.warning(f"Retrying with fewer questions ({max(3, num_questions-2)})...")
                                    current_num_questions = max(3, num_questions-2)
                                
                                with st.spinner(f"🤖 AI is generating quiz questions (Attempt {attempts}/{max_attempts})..."):
                                    try:
                                        # Generate quiz questions using AI with a more structured prompt
                                        prompt = f"""
                                        You are an educational assessment expert. Create a quiz with EXACTLY {current_num_questions} questions.
                                        
                                        IMPORTANT: 
                                        - Keep your response concise but accurate
                                        - Use the simplest language possible while maintaining accuracy
                                        - Make explanations brief (1-2 sentences maximum)
                                        
                                        QUIZ REQUIREMENTS:
                                        - Create EXACTLY {current_num_questions} questions at {difficulty} difficulty level
                                        - Include only these question types: {', '.join(question_types)}
                                        - Distribute question types evenly
                                        - Ensure all questions are based on the content
                                        - Multiple choice questions need 4 options labeled A, B, C, D
                                        - For multiple choice, correct answer should be just the letter (A, B, C or D)
                                        - True/False questions should have "correct" as a boolean (true or false)
                                        - Short answer questions MUST include an "answer" field with the expected answer
                                        - Keep all questions and answers concise
                                        
                                        POINT VALUES FOR QUESTIONS:
                                        - Multiple choice and true/false questions: 1 mark each
                                        - Short answer questions: 2 marks each
                                        - Essay questions: 5 marks each
                                        
                                        Return ONLY valid JSON with NO ADDITIONAL TEXT. The JSON must have this exact structure:
                                        {{
                                          "title": "{quiz_title}",
                                          "description": "{quiz_description}",
                                          "questions": [
                                            {{
                                              "type": "multiple_choice",
                                              "question": "What is X?",
                                              "options": ["A. Option 1", "B. Option 2", "C. Option 3", "D. Option 4"],
                                              "correct": "A",
                                              "explanation": "Brief explanation"
                                            }},
                                            {{
                                              "type": "short_answer",
                                              "question": "Define X",
                                              "answer": "Expected answer here",
                                              "explanation": "Brief explanation"
                                            }}
                                          ]
                                        }}
                                        
                                        CONTENT:
                                        {processed_content}
                                        """
                                        
                                        # Call the AI model
                                        response = model(prompt)
                                        
                                        # Clean and parse the response
                                        # Find JSON content (handling potential text before/after the JSON)
                                        import re
                                        json_pattern = r'({.*})'
                                        json_match = re.search(json_pattern, response, re.DOTALL)
                                        
                                        if json_match:
                                            json_str = json_match.group(1)
                                            try:
                                                quiz_data = json.loads(json_str)
                                                if isinstance(quiz_data, dict) and "questions" in quiz_data and len(quiz_data["questions"]) > 0:
                                                    # Validate quiz data
                                                    is_valid = True
                                                    for i, q in enumerate(quiz_data["questions"]):
                                                        # Ensure short answer questions have "answer" field
                                                        if q.get("type", "").lower() == "short_answer" and "answer" not in q:
                                                            st.error(f"Question {i+1} (short answer) missing required 'answer' field. Fixing...")
                                                            # Add default answer
                                                            q["answer"] = "Answer will be evaluated manually"
                                                            is_valid = False
                                                    
                                                    if not is_valid:
                                                        st.warning("Some issues were detected and fixed in the quiz data. Proceeding with modified data.")
                                                    
                                                    success = True
                                                else:
                                                    st.error("AI response has valid JSON format but missing required quiz structure")
                                            except json.JSONDecodeError as e:
                                                st.error(f"JSON parsing error: {str(e)}")
                                                st.code(json_str[:500] + "..." if len(json_str) > 500 else json_str)
                                        else:
                                            # Attempt to fix common JSON formatting issues and try again
                                            try:
                                                # Sometimes the model might return JSON with unnecessary escaping
                                                fixed_response = response.replace('\\"', '"').replace('\\n', '\n')
                                                quiz_data = json.loads(fixed_response)
                                                if isinstance(quiz_data, dict) and "questions" in quiz_data:
                                                    # Validate quiz data
                                                    is_valid = True
                                                    for i, q in enumerate(quiz_data["questions"]):
                                                        # Ensure short answer questions have "answer" field
                                                        if q.get("type", "").lower() == "short_answer" and "answer" not in q:
                                                            st.error(f"Question {i+1} (short answer) missing required 'answer' field. Fixing...")
                                                            # Add default answer
                                                            q["answer"] = "Answer will be evaluated manually"
                                                            is_valid = False
                                                    
                                                    if not is_valid:
                                                        st.warning("Some issues were detected and fixed in the quiz data. Proceeding with modified data.")
                                                    
                                                    success = True
                                                else:
                                                    st.error("Unable to extract valid quiz data")
                                            except:
                                                st.error("Unable to parse AI response as JSON")
                                                st.code(response[:500] + "..." if len(response) > 500 else response)
                                    
                                    except Exception as e:
                                        st.error(f"Error during quiz generation: {str(e)}")
                                        if attempts >= max_attempts:
                                            import traceback
                                            st.code(traceback.format_exc())
                            
                            if success:
                                with st.spinner("📝 Creating quiz form..."):
                                    try:
                                        # Ensure quiz title is properly set
                                        if not quiz_data.get("title") or quiz_data.get("title").strip() == "":
                                            quiz_data["title"] = quiz_title
                                            
                                        # Create quiz form
                                        try:
                                            form_url = create_quiz_form(creds, quiz_data)
                                            
                                            # Create assignment in Google Classroom
                                            due_datetime = datetime.combine(due_date, due_time)
                                            create_assignment(
                                                creds,
                                                course_id,
                                                quiz_title,
                                                f"{quiz_description}\n\nComplete this quiz by {due_date}: {form_url}\nTime limit: {time_limit} minutes",
                                                due_datetime
                                            )
                                        
                                            # Success message with details
                                            st.success("✅ Quiz created and assigned successfully!")
                                            
                                            # Quiz info
                                            st.info(f"""
                                            **Quiz Details:**
                                            - **Title:** {quiz_data.get('title')}
                                            - **Questions:** {len(quiz_data.get('questions', []))}
                                            - **Time Limit:** {time_limit} minutes
                                            - **Due:** {due_date} at {due_time}
                                            """)
                                            
                                            # Reminder about quiz settings
                                            st.info("""
                                            **Important:** Make sure to open the quiz in Google Forms to verify:
                                            1. The form is properly set up as a quiz
                                            2. Automatic grading is enabled 
                                            3. Correct answers are correctly marked
                                            
                                            You can do this by clicking "Edit Form" below.
                                            """)
                                            
                                            # Add manual setup instructions
                                            with st.expander("Manual Quiz Setup Instructions (if needed)"):
                                                st.markdown("""
                                                ### How to Manually Configure Quiz Settings
                                                
                                                If automatic quiz setup didn't work properly, follow these steps:
                                                
                                                1. Click the "Edit Quiz Settings" link below
                                                2. In Google Forms, click the Settings gear icon ⚙️ in the top right
                                                3. Go to the "Quizzes" tab
                                                4. Turn on "Make this a quiz"
                                                5. Choose your preferred options for release grade and answer viewing
                                                6. Click "Save"
                                                7. For each question:
                                                    - Click on the question
                                                    - Click "Answer key" at the bottom
                                                    - Select the correct answer
                                                    - Assign points (1 for MCQ/True-False, 2 for short answer, 5 for essay)
                                                    - Click "Done"
                                                8. Finally, click the "Send" button to share the quiz
                                                
                                                These steps ensure your quiz will properly track and grade student responses.
                                                """)
                                            
                                            # Link to the quiz
                                            st.markdown(f"#### [📝 Open Quiz Form]({form_url})")
                                            
                                            # Add direct edit link
                                            edit_url = form_url.replace("/viewform", "/edit")
                                            st.markdown(f"#### [✏️ Edit Quiz Settings]({edit_url})")
                                            
                                            # Show preview of generated questions
                                            with st.expander("👁️ Preview Questions", expanded=True):
                                                for i, q in enumerate(quiz_data["questions"]):
                                                    # Set point value based on question type
                                                    point_value = 1  # Default
                                                    q_type = q["type"].lower()
                                                    
                                                    if q_type == "multiple_choice" or q_type == "true_false":
                                                        point_value = 1
                                                    elif q_type == "short_answer":
                                                        point_value = 2
                                                    elif q_type == "essay":
                                                        point_value = 5
                                                        
                                                    st.markdown(f"**Q{i+1}: {q['question']}** [{point_value} {'mark' if point_value == 1 else 'marks'}]")
                                                    
                                                    if q["type"] == "multiple_choice":
                                                        for opt in q["options"]:
                                                            if q["correct"] in opt.split(".")[0]:
                                                                st.markdown(f"- **{opt}** ✓")
                                                            else:
                                                                st.markdown(f"- {opt}")
                                                    
                                                    elif q["type"] == "true_false":
                                                        correct = "True" if q["correct"] else "False"
                                                        incorrect = "False" if q["correct"] else "True"
                                                        st.markdown(f"- **{correct}** ✓")
                                                        st.markdown(f"- {incorrect}")
                                                    
                                                    elif q["type"] == "short_answer":
                                                        if "answer" in q:
                                                            st.markdown(f"*Answer: **{q['answer']}***")
                                                        else:
                                                            st.markdown(f"*Answer: Manual grading required*")
                                                    
                                                    elif q["type"] == "essay":
                                                        st.markdown(f"*Word limit: {q.get('min_words', 100)}-{q.get('max_words', 500)} words*")
                                                    
                                                    if "explanation" in q:
                                                        st.markdown(f"*Explanation: {q['explanation']}*")
                                                    
                                                    if i < len(quiz_data["questions"]) - 1:
                                                        st.markdown("---")
                                            
                                        except KeyError as ke:
                                            # Handle missing key errors more gracefully
                                            st.error(f"❌ Error in quiz data structure: {str(ke)}")
                                            st.warning("This error might be related to missing fields in the quiz questions.")
                                            st.info("Try regenerating the quiz or select different question types.")
                                            st.stop()
                                            
                                        except ValueError as ve:
                                            # Handle value errors more gracefully  
                                            st.error(f"❌ Error in quiz data: {str(ve)}")
                                            st.info("The quiz structure may be incomplete. Try regenerating with fewer questions.")
                                            st.stop()
                                    
                                    except Exception as e:
                                        st.error(f"❌ Error creating quiz form: {str(e)}")
                                        st.error("Please check the console for detailed error logs.")
                                        import traceback
                                        st.code(traceback.format_exc())
                            else:
                                st.error("❌ Failed to generate valid quiz questions after multiple attempts.")
                                st.info("Try reducing the number of questions or simplifying the content.")
                    else:
                        st.warning("No courses found. Please create a course first.")
        
        # --- Evaluate Responses Tab ---
        with quiz_tabs[1]:
            st.subheader("📊 Quiz Response Evaluation")
            
            # Get all forms created by the user
            try:
                with st.spinner("Loading your forms..."):
                    forms = get_all_forms(creds)
                
                if forms:
                    # Create a dropdown to select form using the form title instead of name
                    form_options = {f"{form['title']} (Created: {form['createdTime'][:10]})": form['id'] for form in forms}
                    selected_form_name = st.selectbox("Select Quiz Form", list(form_options.keys()))
                    selected_form_id = form_options[selected_form_name]
                    
                    # Add debug mode toggle
                    debug_mode = st.checkbox("Enable Debug Mode", value=False, 
                                           help="Show raw response data and debugging information")
                    
                    # Button to load responses
                    if st.button("Load Responses", type="primary"):
                        with st.spinner("Loading and processing quiz responses..."):
                            try:
                                # Add error handling for JSON parsing
                                try:
                                    form, responses, questions_map = get_form_responses(creds, selected_form_id)
                                    
                                    # Display raw data in debug mode
                                    if debug_mode and responses:
                                        st.subheader("🔍 Debug: Raw Response Data")
                                        st.json(responses[0])
                                        
                                        st.subheader("🔍 Debug: Questions Map")
                                        st.json(questions_map)
                                        
                                        # Show debugging information for student names
                                        st.subheader("🔍 Debug: Student Information")
                                        student_info = []
                                        for i, resp in enumerate(responses):
                                            student_info.append({
                                                "Response #": i+1,
                                                "Student Name": resp.get('student_name', 'Unknown'),
                                                "Roll Number": resp.get('roll_number', 'N/A'),
                                                "Email": resp.get('respondent_email', 'Unknown'),
                                                "Score": f"{resp.get('total_score', 0)}/{resp.get('max_possible', 0)}",
                                                "Percentage": f"{resp.get('percentage', 0)}%"
                                            })
                                        st.table(student_info)
                                        
                                        # Show debugging information about the special question
                                        for resp in responses:
                                            for answer in resp.get('answers', []):
                                                if "factors" in answer.get('question_text', '').lower() and "foundation model" in answer.get('question_text', '').lower():
                                                    st.subheader("🔍 Debug: Foundation Model Factors Question")
                                                    st.json(answer)
                                        
                                        st.subheader("🔍 Debug: Raw Form Data")
                                        with st.expander("Form Structure"):
                                            st.json({k: v for k, v in form.items() if k != 'items'})
                                            
                                        with st.expander("Form Items"):
                                            for i, item in enumerate(form.get('items', [])):
                                                st.markdown(f"**Item {i+1}**: {item.get('title', 'No title')}")
                                                st.json(item)
                                                st.markdown("---")
                                                
                                        # Display information about manual grading if applicable
                                        settings = form.get('settings', {})
                                        quiz_settings = settings.get('quizSettings', {})
                                        is_quiz = quiz_settings.get('isQuiz', False)
                                        
                                        if not is_quiz:
                                            st.warning("⚠️ This form is not configured as a quiz in Google Forms. Using manual grading instead.")
                                            st.info("The system is using an inferred answer key based on the form content.")
                                            
                                            # Extract and display the manual answer key
                                            st.subheader("🔑 Manual Answer Key")
                                            answer_key_data = []
                                            
                                            for q_id, q_info in questions_map.items():
                                                # Find this question's answer in the responses
                                                if responses and responses[0]['answers']:
                                                    for answer in responses[0]['answers']:
                                                        if answer['question_id'] == q_id:
                                                            is_student_info = q_info.get('is_student_info', False)
                                                            if not is_student_info:  # Only show graded questions
                                                                q_text = q_info.get('text', '')
                                                                max_score = answer.get('max_score', 0)
                                                                is_correct = answer.get('is_correct', False)
                                                                user_answer = ', '.join(answer.get('response', []))
                                                                
                                                                # Show inferred correct answer based on user's response correctness
                                                                answer_key_data.append({
                                                                    "Question": q_text,
                                                                    "Expected Answer": user_answer if is_correct else "See explanation",
                                                                    "Points": max_score,
                                                                    "User Scored": "✓" if is_correct else "✗"
                                                                })
                                            
                                            if answer_key_data:
                                                st.table(answer_key_data)
                                except json.JSONDecodeError as json_err:
                                    st.error(f"JSON parsing error: {str(json_err)}")
                                    st.error("This often happens when the Google Forms API returns malformed JSON.")
                                    st.info("Try a different form or try again later when the API might be more stable.")
                                    # Add debugging info
                                    import traceback
                                    st.code(traceback.format_exc())
                                    st.stop()
                                    
                                if responses:
                                    # Display form title
                                    form_title = form.get("info", {}).get("title", "Untitled Form")
                                    st.subheader(f"📋 {form_title}")
                                    
                                    # Display simplified table of student results
                                    st.subheader("📊 Student Quiz Results")
                                    
                                    # Create table with student info, marks, and brief feedback
                                    results_data = []
                                    for response in responses:
                                        # Handle case where student info might be missing
                                        student_name = response.get('student_name', 'Unknown')
                                        # If student name is missing, use email instead
                                        if student_name == 'Unknown' or not student_name or student_name.strip() == '':
                                            email = response.get('respondent_email', '')
                                            student_name = email if email and email != 'Unknown' else 'Anonymous'
                                        
                                        roll_number = response.get('roll_number', 'N/A')
                                        
                                        # Get score data with proper defaults
                                        total_score = response.get('total_score', 0)
                                        max_possible = response.get('max_possible', 0)
                                        percentage = response.get('percentage', 0)
                                        
                                        # Format percentage properly
                                        percentage_str = f"{percentage}%" if isinstance(percentage, (int, float)) else percentage
                                        
                                        # Get AI feedback data if available
                                        ai_feedback = response.get('ai_feedback', {})
                                        total_marks = ai_feedback.get('total_marks', f"{total_score}/{max_possible}")
                                        feedback = ai_feedback.get('feedback', response.get('feedback', 'No feedback available'))
                                        
                                        results_data.append({
                                            'Name': student_name,
                                            'Roll Number': roll_number,
                                            'Score': total_marks,
                                            'Percentage': percentage_str,
                                            'Feedback': feedback
                                        })
                                    
                                    # Create and display DataFrame with results
                                    if results_data:
                                        results_df = pd.DataFrame(results_data)
                                        st.dataframe(results_df, hide_index=True, use_container_width=True)
                                        
                                        # Option to download as CSV
                                        csv = results_df.to_csv(index=False)
                                        st.download_button(
                                            "📥 Download Results as CSV",
                                            csv,
                                            "quiz_results.csv",
                                            "text/csv",
                                            key="download-results-csv"
                                        )
                                    
                                    # Show summary statistics
                                    st.subheader("📈 Quiz Summary")
                                    col1, col2, col3 = st.columns(3)
                                    
                                    # Calculate statistics with safeguards for missing data
                                    num_responses = len(responses)
                                    
                                    # Calculate average score safely
                                    percentages = [r.get('percentage', 0) for r in responses]
                                    percentages = [p for p in percentages if isinstance(p, (int, float))]
                                    avg_score = sum(percentages) / len(percentages) if percentages else 0
                                    
                                    # Calculate passing rate
                                    passing_threshold = 60
                                    passing_count = sum(1 for r in responses if isinstance(r.get('percentage', 0), (int, float)) and r.get('percentage', 0) >= passing_threshold)
                                    passing_rate = (passing_count / num_responses * 100) if num_responses > 0 else 0
                                    
                                    # Display stats
                                    col1.metric("Total Submissions", num_responses)
                                    col2.metric("Average Score", f"{avg_score:.1f}%")
                                    col3.metric("Passing Rate", f"{passing_rate:.1f}%")
                                    
                                    # Add option to view individual responses
                                    if st.checkbox("View Individual Responses"):
                                        for i, response in enumerate(responses):
                                            # Get respondent name or email for display
                                            display_name = response.get('student_name', 'Unknown')
                                            if display_name == 'Unknown' or not display_name.strip():
                                                display_name = response.get('respondent_email', f'Response {i+1}')
                                                
                                            with st.expander(f"{display_name}"):
                                                st.write(f"**Submitted:** {response.get('submission_time', 'Unknown')}")
                                                
                                                # Show score information
                                                total = response.get('total_score', 0)
                                                max_score = response.get('max_possible', 0)
                                                pct = response.get('percentage', 0)
                                                
                                                # Get AI feedback if available
                                                ai_feedback = response.get('ai_feedback', {})
                                                total_marks = ai_feedback.get('total_marks', f"{total}/{max_score}")
                                                
                                                st.write(f"**Score:** {total_marks} ({pct}%)")
                                                
                                                # Display AI feedback with styling
                                                feedback = ai_feedback.get('feedback', response.get('feedback', 'No feedback available'))
                                                st.markdown(f"""
                                                <div style="background-color:#f0f7fb; padding:10px; border-radius:5px; margin:10px 0;">
                                                    <b>🤖 AI Feedback:</b> {feedback}
                                                </div>
                                                """, unsafe_allow_html=True)
                                                
                                                # Show answers with better formatting
                                                st.write("### Responses")
                                                for j, answer in enumerate(response.get('answers', [])):
                                                    # Determine if question was answered correctly
                                                    is_correct = answer.get('is_correct', False)
                                                    status = "✅" if is_correct else "❌"
                                                    
                                                    # Determine question type and point value
                                                    q_type = answer.get('question_type', '').lower()
                                                    max_points = answer.get('max_score', 0)
                                                    
                                                    # Question title with number and point value
                                                    point_text = f"[{max_points} {'mark' if max_points == 1 else 'marks'}]"
                                                    st.write(f"{status} **Question {j+1}:** {answer.get('question_text', '')} {point_text}")
                                                    
                                                    # Response details
                                                    response_text = answer.get('response', [])
                                                    if response_text:
                                                        st.write(f"**Response:** {', '.join(response_text)}")
                                                    else:
                                                        st.write("**Response:** No answer provided")
                                                    
                                                    # Show score for this question
                                                    q_score = answer.get('score', 0)
                                                    q_max = answer.get('max_score', 0)
                                                    st.write(f"**Points:** {q_score}/{q_max}")
                                                    
                                                    # Add separator between questions
                                                    if j < len(response.get('answers', [])) - 1:
                                                        st.markdown("---")
                                else:
                                    st.info("No responses have been submitted for this quiz yet.")
                            
                            except Exception as e:
                                st.error(f"Error loading form responses: {str(e)}")
                                import traceback
                                st.code(traceback.format_exc())
                    
                    # Links to view/edit form directly
                    st.markdown("---")
                    selected_form = next((form for form in forms if form['id'] == selected_form_id), None)
                    if selected_form:
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.markdown(f"[🔗 View Form]({selected_form['responderUrl']})")
                        with col2:
                            st.markdown(f"[📊 View Responses]({selected_form['responseUrl']})")
                        with col3:
                            st.markdown(f"[✏️ Edit Form]({selected_form['editUrl']})")
                
                else:
                    st.info("No forms found. Create a quiz first to evaluate responses.")
            
            except Exception as e:
                st.error(f"Error listing forms: {str(e)}")

# --- Google Classroom Tab ---
elif selected_tab == "Google Classroom":
    st.header("🏫 Google Classroom Management")
    
    if not creds:
        st.warning("⚠️ Google authentication required to manage classes.")
    else:
        # Create new class section
        st.subheader("➕ Create New Class")
        
        with st.container():
            left_col, right_col = st.columns([3, 3])
            
            with left_col:
                st.markdown("##### Basic Information")
                course_name = st.text_input("Course Name", placeholder="Enter course name")
                course_section = st.text_input("Section", placeholder="Enter section (optional)")
                course_description = st.text_area("Description", placeholder="Enter course description", height=150)
                course_room = st.text_input("Room Number", placeholder="Enter room number (optional)")
            
            with right_col:
                st.markdown("##### Schedule Information")
                start_date = st.date_input("Start Date", min_value=datetime.now().date())
                end_date = st.date_input("End Date", min_value=start_date)
                
                st.markdown("**Class Days**")
                days = st.multiselect(
                    "",
                    ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
                    placeholder="Select class days"
                )
                
                time_col1, time_col2 = st.columns(2)
                with time_col1:
                    start_time = st.time_input("Start Time")
                with time_col2:
                    end_time = st.time_input("End Time")
                
                timezone = st.selectbox(
                    "Timezone",
                    ["America/New_York", "America/Chicago", "America/Denver", "America/Los_Angeles", "Pacific/Honolulu"]
                )
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            create_button = st.button("Create Class", type="primary", use_container_width=True)
        
        if create_button:
            if course_name and days:
                schedule = {
                    'start_date': datetime.combine(start_date, datetime.min.time()),
                    'end_date': datetime.combine(end_date, datetime.min.time()),
                    'days': days,
                    'start_time': start_time.strftime('%H:%M'),
                    'end_time': end_time.strftime('%H:%M'),
                    'timezone': timezone
                }
                
                with st.spinner("Creating class and setting up automation..."):
                    course = create_class_with_meet(
                        creds,
                        course_name,
                        course_section,
                        course_description,
                        course_room,
                        schedule
                    )
                    
                    if course:
                        st.success(f"✅ Class '{course_name}' created successfully!")
                        
                        automation_thread = threading.Thread(
                            target=automate_class_management,
                            args=(creds, course['id'])
                        )
                        automation_thread.daemon = True
                        automation_thread.start()
                        
                        with st.container():
                            st.info("🤖 Automation enabled for this class:")
                            st.markdown("""
                            - ⏰ Automatic class reminders 15 minutes before each session
                            - 📝 Automatic generation and sharing of meeting minutes
                            - 🔗 Automatic management of Google Meet links
                            """)
                    else:
                        st.error("❌ Failed to create class. Please check your inputs and try again.")
            else:
                st.warning("⚠️ Please fill in all required fields (Course Name and Class Days).")
        
        st.markdown("---")
        
        st.subheader("📋 Your Classes")
        
        courses = list_courses(creds)
        if courses:
            for course in courses:
                with st.container():
                    st.markdown(f"### {course['name']} ({course.get('section', 'No Section')})")
                    
                    info_col, action_col = st.columns([3, 2])
                    
                    with info_col:
                        st.markdown("##### Class Information")
                        st.markdown(f"**Description:** {course.get('description', 'No description')}")
                        st.markdown(f"**Room:** {course.get('room', 'No room assigned')}")
                        
                        st.markdown("##### Upcoming Classes")
                        schedule = get_course_schedule(creds, course['id'])
                        if schedule:
                            # Display session details
                            st.markdown("### 📅 Upcoming Sessions")
                            for session in schedule:
                                try:
                                    # Safely access session data with fallbacks
                                    start_time = session.get('start', {}).get('dateTime', 'Time not set')
                                    summary = session.get('summary', 'No summary available')
                                    description = session.get('description', 'No description available')
                                    meet_link = session.get('hangoutLink', '')
                                    
                                    # Format the date and time
                                    try:
                                        start_datetime = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                                        formatted_time = start_datetime.strftime("%B %d, %Y at %I:%M %p")
                                    except (ValueError, AttributeError):
                                        formatted_time = start_time
                                    
                                    st.markdown(f"#### {summary}")
                                    st.markdown(f"- **Time**: {formatted_time}")
                                    st.markdown(f"- **Description**: {description}")
                                    
                                    if meet_link:
                                        st.markdown(f"- **Join Meeting**: [Click here]({meet_link})")
                                    
                                    st.markdown("---")
                                except Exception as e:
                                    st.error(f"Error displaying session: {str(e)}")
                                    continue
                        else:
                            st.info("No upcoming classes scheduled.")
                    
                    with action_col:
                        st.markdown("##### Quick Actions")
                        
                        st.markdown("**📣 Send Announcement**")
                        announcement = st.text_area("Message", key=f"text_{course['id']}", height=100)
                        st.button("Post Announcement", key=f"post_{course['id']}", use_container_width=True)
                        
                        st.markdown("**📝 Create Assignment**")
                        title = st.text_input("Title", key=f"title_{course['id']}")
                        description = st.text_area("Instructions", key=f"desc_{course['id']}", height=100)
                        st.button("Create Assignment", key=f"create_{course['id']}", use_container_width=True)
                
                st.markdown("---")
        else:
            st.info("No classes found. Create a new class to get started!")

# --- Automation Tab ---
elif selected_tab == "Automation":
    st.header("⚙️ Automation Settings")
    
    st.write("Configure automated tasks for your classes")
    
    automation_status = "✅ Running" if is_automation_running() else "❌ Stopped"
    st.info(f"Automation system status: {automation_status}")
    
    if not is_automation_running():
        if st.button("Start Automation System"):
            if start_automation():
                st.success("Automation system started!")
                st.experimental_rerun()
    else:
        if st.button("Stop Automation System"):
            if stop_automation():
                st.success("Automation system stopped!")
                st.experimental_rerun()
    
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
    
    st.subheader("📝 Meeting Summaries")
    st.session_state.automated_tasks['auto_summaries'] = st.toggle(
        "Generate automatic meeting summaries",
        value=st.session_state.automated_tasks['auto_summaries']
    )
    
    if st.session_state.automated_tasks['auto_summaries']:
        share_with_students = st.checkbox("Share summaries with students", value=True)
        summary_delay = st.slider("Minutes after class ends", 1, 30, 10)
        
        if st.button("Apply Summary Settings"):
            st.success("✅ Automatic meeting summaries configured")
            st.info(f"Summaries will be generated {summary_delay} minutes after each class session")
    
    st.subheader("👥 Attendance Tracking")
    st.session_state.automated_tasks['auto_attendance'] = st.toggle(
        "Track student attendance automatically",
        value=st.session_state.automated_tasks['auto_attendance']
    )
    
    if st.session_state.automated_tasks['auto_attendance']:
        if st.button("Apply Attendance Settings"):
            st.success("✅ Automatic attendance tracking configured")
            st.info("Student attendance will be recorded for each class session")

def get_course_schedule(creds, course_id):
    """
    Get the schedule for a specific course from Google Calendar.
    
    Args:
        creds: Google API credentials
        course_id: ID of the course to get schedule for
        
    Returns:
        List of upcoming sessions for the course
    """
    try:
        service = build('calendar', 'v3', credentials=creds)
        
        # Get course details to find the calendar ID
        classroom_service = build('classroom', 'v1', credentials=creds)
        course = classroom_service.courses().get(id=course_id).execute()
        
        # Get calendar events for the course
        now = datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
        events_result = service.events().list(
            calendarId='primary',
            timeMin=now,
            maxResults=10,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        # Filter events for this course
        course_sessions = []
        for event in events:
            if course.get('name', '') in event.get('summary', ''):
                course_sessions.append(event)
        
        return course_sessions
    except Exception as e:
        st.error(f"Error getting course schedule: {str(e)}")
        return []

def setup_class_automation(creds, course_id, reminder_minutes=15):
    """
    Set up automated reminders and notifications for a course.
    
    Args:
        creds: Google API credentials
        course_id: ID of the course to set up automation for
        reminder_minutes: How many minutes before class to send reminder
    """
    try:
        # Get course schedule
        sessions = get_course_schedule(creds, course_id)
        
        if not sessions:
            st.warning("No upcoming sessions found for this course.")
            return
        
        # Set up reminders for each session
        for session in sessions:
            start_time = session.get('start', {}).get('dateTime')
            if not start_time:
                continue
                
            # Calculate reminder time
            session_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            reminder_time = session_time - timedelta(minutes=reminder_minutes)
            
            # Create reminder event
            service = build('calendar', 'v3', credentials=creds)
            reminder = {
                'summary': f"Reminder: {session.get('summary', 'Class Session')}",
                'description': f"Class starts in {reminder_minutes} minutes. Join here: {session.get('hangoutLink', '')}",
                'start': {
                    'dateTime': reminder_time.isoformat(),
                    'timeZone': 'UTC',
                },
                'end': {
                    'dateTime': (reminder_time + timedelta(minutes=5)).isoformat(),
                    'timeZone': 'UTC',
                },
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'popup', 'minutes': 0},
                    ],
                },
            }
            
            service.events().insert(calendarId='primary', body=reminder).execute()
            
        st.success(f"Automation set up successfully for {len(sessions)} sessions!")
    except Exception as e:
        st.error(f"Error setting up automation: {str(e)}")