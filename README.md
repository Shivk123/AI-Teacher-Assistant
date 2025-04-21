# Save the README content to a downloadable file

readme_content = """# 🧑‍🏫 Teacher Assistant App

An AI-powered web application designed to automate and simplify routine teaching tasks—built in just **one hour** during the **5-Day Generative AI Intensive** by **Google & Kaggle**. This project leverages **Gemini AI** and **Google Cloud services** to empower educators with intelligent tools for classroom management, quiz creation, grading, and more.

---

## 🚀 Project Highlights

- ⏱️ **Built in ~1 hour** thanks to the seamless integration of Google Workspace APIs
- 💡 Powered by **Gemini AI (Vertex AI)** for intelligent content generation
- 📚 Integrates directly with **Google Classroom, Forms, Calendar, Meet**, and **Drive**
- 🎓 Designed to save teachers hours every week by automating repetitive workflows

---

## 📦 Features

### 📊 Dashboard

- Overview of today's classes
- Quick access to Google Meet links
- One-click reminders
- Status panel for automations (reminders, summaries, attendance)

### 📝 Quiz Creator

- Upload PDFs (textbooks, lecture notes)
- Configure question types, difficulty, and parameters
- AI generates Google Form quizzes with answer keys
- Automatically posts quiz to Google Classroom

### 🧮 Evaluate Responses

- Connects to Forms and fetches student submissions
- Generates scores and class performance summaries
- Uses Gemini AI to create **personalized feedback**
- Exports results to CSV

### 🏫 Classroom Manager

- Create and manage Google Classroom courses
- Schedule recurring classes
- Post announcements and assignments from within the app

### 🤖 Automations

- Auto reminders before classes
- Auto summaries after sessions
- Attendance tracking using Google Meet & Calendar data

---

## 🧠 Built With

- **Gemini Pro API (Vertex AI)** – Prompt-based content generation
- **Google Workspace APIs:**
  - Google Classroom API
  - Google Forms API
  - Google Calendar API
  - Google Drive API
  - Google Meet API
- **Google Cloud Platform (GCP):**
  - Google Cloud Storage – File uploads and resource management
  - OAuth 2.0 & Service Accounts – Secure authentication
- **Python / JavaScript (or your frontend tech)** – App logic & UI
- **Flask / Node / Streamlit / React** – (depending on your tech stack)

---

## 🔧 Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/teacher-assistant-app.git
cd teacher-assistant-app
```

### 2. Set Up Google Cloud Credentials

#### a. Enable APIs in Google Cloud Console

- Go to [Google Cloud Console](https://console.cloud.google.com/)
- Enable the following APIs:
  - Vertex AI API
  - Google Classroom API
  - Google Forms API
  - Google Calendar API
  - Google Drive API

#### b. Create OAuth 2.0 Credentials

- Go to **APIs & Services > Credentials**
- Click **"Create Credentials" > OAuth client ID**
- Choose **"Web application"** and add authorized redirect URIs if needed
- Download the `credentials.json` file and place it in your project directory

#### c. Get API Key from Google Studio

- Visit [Google API Console](https://console.cloud.google.com/apis/credentials)
- Click **"Create credentials" > API key**
- Use this API key in your `.env` or config file as needed
