from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# ✅ List all courses
def list_courses(creds):
    service = build('classroom', 'v1', credentials=creds)
    results = service.courses().list().execute()
    return results.get('courses', [])

# ✅ Create a new assignment
def create_assignment(creds, course_id, title, description):
    service = build('classroom', 'v1', credentials=creds)
    coursework = {
        'title': title,
        'description': description,
        'workType': 'ASSIGNMENT',
        'state': 'PUBLISHED'
    }
    return service.courses().courseWork().create(courseId=course_id, body=coursework).execute()

# 🆕 Create a new course
def create_course(creds, name, section=None, description=None, room=None):
    service = build('classroom', 'v1', credentials=creds)
    course = {
        'name': name,
        'section': section,
        'description': description,
        'room': room,
        'ownerId': 'me'  # Will be set to the authenticated user
    }
    try:
        created_course = service.courses().create(body=course).execute()
        return created_course
    except HttpError as error:
        print(f"An error occurred: {error}")
        return None

# 🆕 Add a teacher to a course
def add_teacher(creds, course_id, teacher_email):
    service = build('classroom', 'v1', credentials=creds)
    teacher = {'userId': teacher_email}
    try:
        return service.courses().teachers().create(courseId=course_id, body=teacher).execute()
    except HttpError as error:
        print(f"Failed to add teacher: {error}")
        return None

# 🆕 Add a student to a course
def add_student(creds, course_id, student_email):
    service = build('classroom', 'v1', credentials=creds)
    student = {'userId': student_email}
    try:
        return service.courses().students().create(courseId=course_id, body=student).execute()
    except HttpError as error:
        print(f"Failed to add student: {error}")
        return None

# 🆕 Post an announcement in the course stream
def post_announcement(creds, course_id, text):
    service = build('classroom', 'v1', credentials=creds)
    announcement = {
        'text': text
    }
    try:
        return service.courses().announcements().create(courseId=course_id, body=announcement).execute()
    except HttpError as error:
        print(f"Failed to post announcement: {error}")
        return None
