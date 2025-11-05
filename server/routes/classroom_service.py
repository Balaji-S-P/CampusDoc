from flask import Blueprint, request, jsonify
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
import requests
from db_utils.db_helper import get_tokens, save_tokens


def get_classroom_service(user_id):
    print(f"Getting email service for user_id: {user_id}")
    token_data = get_tokens(user_id)
    if not token_data:
        raise Exception("No tokens found for user")
    
    print(f"Token data found: {list(token_data.keys())}")
    
    # Convert the stored token data back to a Credentials object
    creds = Credentials(
        token=token_data['access_token'],
        refresh_token=token_data['refresh_token'],
        token_uri=token_data.get('token_uri', 'https://oauth2.googleapis.com/token'),
        client_id=token_data.get('client_id'),
        client_secret=token_data.get('client_secret'),
        scopes=token_data['scopes']
    )
    
    # Refresh the credentials if needed
    if creds.expired and creds.refresh_token:
        print("Credentials expired, refreshing...")
        creds.refresh(requests.Request())
        print("Credentials refreshed successfully")
        
        # Save the refreshed tokens back to the database
        try:
            save_tokens(user_id, creds, token_data.get('email', ''))
            print("Refreshed tokens saved to database")
        except Exception as e:
            print(f"Warning: Could not save refreshed tokens: {e}")
    
    print(f"Credentials created, scopes: {creds.scopes}")
    service = build('classroom', 'v1', credentials=creds)
    print(f"Service object type: {type(service)}")
    print(f"Service has users method: {hasattr(service, 'users')}")
    
    return service


def list_courses(user_id=None):
    """
    Lists all courses for the user
    course_id can be fetched using list_courses(user_id) function
    """
    try:
        service = get_classroom_service(user_id)
        result = service.courses().list().execute()
        courses = result.get('courses', [])
        return courses
    except Exception as e:
        return {"error": f"Failed to get courses: {str(e)}"}

def list_course_students(course_id, user_id=None):
    """
    Lists all students for a course
    student_id can be fetched using list_course_students(course_id) function
    """
    try:
        service = get_classroom_service(user_id)
        result = service.courses().students().list(courseId=course_id).execute()
        students = result.get('students', [])
        return students
    except Exception as e:
        return {"error": f"Failed to get students: {str(e)}"}

def get_student(course_id,student_id, user_id=None):
    """student_id can be email of student or student id
    course_id can be fetched using list_courses(user_id) function
    student_id can be fetched using list_course_students(course_id) function
    """
    try:
        service = get_classroom_service(user_id)
        result = service.courses().students().get(courseId=course_id, userId=student_id).execute()
        return result
    except Exception as e:
        return {"error": f"Failed to get student: {str(e)}"}

def list_student_submissions(course_id, student_id, user_id=None):
    """student_id can be email of student or student id
    course_id can be fetched using list_courses(user_id) function
    student_id can be fetched using list_course_students(course_id) function
    """
    try:
        service = get_classroom_service(user_id)
        # First get all coursework for the course
        coursework_result = service.courses().courseWork().list(courseId=course_id).execute()
        coursework_list = coursework_result.get('courseWork', [])
        
        all_submissions = []
        for coursework in coursework_list:
            coursework_id = coursework.get('id')
            print(f"Coursework_id: {coursework_id} and course_id: {course_id} and student_id: {student_id}")
            if coursework_id:
                # Get submissions for this specific coursework
                try:
                    submissions_result = service.courses().courseWork().studentSubmissions().list(
                        courseId=course_id, 
                        courseWorkId=coursework_id,
                        userId=student_id
                    ).execute()
                    submissions = submissions_result.get('studentSubmissions', [])
                    all_submissions.extend(submissions)
                except Exception as e:
                    print(f"Failed to get submissions for coursework_id: {coursework_id} and course_id: {course_id} and student_id: {student_id}: {str(e)}")
        return all_submissions
    except Exception as e:
        return {"error": f"Failed to get submissions: {str(e)}"}

def get_coursework(course_id,coursework_id, user_id=None):
    """course_id can be fetched using list_courses(user_id) function
    coursework_id can be fetched using list_student_submissions(course_id,student_id) function
    """
    try:
        print(f"Getting coursework for course_id: {course_id} and coursework_id: {coursework_id}")
        service = get_classroom_service(user_id)
        result = service.courses().courseWork().get(courseId=course_id, id=coursework_id).execute()
        coursework = result
        return coursework
    except Exception as e:
        return {"error": f"Failed to get coursework: {str(e)}"}

def get_coursework_materials(course_id,coursework_id, user_id=None):
    """course_id can be fetched using list_courses(user_id) function
    coursework_id can be fetched using list_student_submissions(course_id,student_id) function
    """
    try:
        service = get_classroom_service(user_id)
        result = service.courses().courseWork().get(courseId=course_id, id=coursework_id).execute()
        coursework = result.get('materials', [])
        return coursework
    except Exception as e:
        return {"error": f"Failed to get coursework materials: {str(e)}"}

def list_courseworks(course_id, user_id=None):
    """course_id can be fetched using list_courses(user_id) function
    coursework_id can be fetched using list_courseworks(course_id) function
    """
    try:
        service = get_classroom_service(user_id)
        result = service.courses().courseWork().list(courseId=course_id).execute()
        coursework = result.get('courseWork', [])
        return coursework
    except Exception as e:
        return {"error": f"Failed to get coursework materials: {str(e)}"}

def create_announcement(course_id, announcement_body, materials, user_id=None):
    """course_id can be fetched using list_courses(user_id) function
    announcement_body={
        "course_id": 1234567890,
        "materials": [],
        "text": "This is a test announcement"
    }
    materials is an array of objects with the following properties:
    {
        "driveFile": {
            "driveFile": {
                "alternateLink": "https://www.google.com"
            }
        }
    }
    {
        "link": {
            "url": "https://www.google.com"
        }
    }
    """
    try:
        service = get_classroom_service(user_id)
        announcement_body['materials'] = materials
        result = service.courses().announcements().create(courseId=course_id, body=announcement_body).execute()
        announcement = result
        return announcement
    except Exception as e:
        return {"error": f"Failed to create announcement: {str(e)}"}

def create_coursework(course_id, coursework_body, user_id=None):
    """course_id can be fetched using list_courses(user_id) function
    coursework_body={
        "courseId": 1234567890,
        "title": "123456",
        "description": "This is a test coursework",
        "materials": [{
        "driveFile": {
            "driveFile": {
                "id": "1ABC123DEF456GHI789",
"title": "test.pdf",
                "alternateLink": "https://www.google.com"
            }
        }
    },
    {
        "link": {
            "url": "https://www.google.com"
        }
    }],
    "state": "PUBLISHED",
        "dueDate": {
            "year": 2025,
            "month": 12,
            "day": 31
        },
        "dueTime": {
            "hours": 12,
            "minutes": 0,
            "seconds": 0,
            "nanos": 0
        },
    "maxPoints": 100,
    "workType": "ASSIGNMENT",
    "assigneeMode": "INDIVIDUAL_STUDENTS",
    "submissionModificationMode": "MODIFIABLE_UNTIL_TURNED_IN",
    "individualStudentsOptions": {
        "studentIds": ["1234567890","1234567891","1234567892"]
    },


    }
    """
    try:
        # Ensure due date is in the future
        from datetime import datetime, timedelta
        current_date = datetime.now()
        future_date = current_date + timedelta(days=7)  # At least 1 week from now
        
        # Update due date if it's not in the future
        if 'dueDate' in coursework_body:
            due_date = coursework_body['dueDate']
            due_datetime = datetime(
                year=due_date.get('year', future_date.year),
                month=due_date.get('month', future_date.month),
                day=due_date.get('day', future_date.day)
            )
            
            # If due date is in the past or today, set it to future
            if due_datetime <= current_date:
                coursework_body['dueDate'] = {
                    'year': future_date.year,
                    'month': future_date.month,
                    'day': future_date.day
                }
                print(f"Updated due date to future date: {future_date.strftime('%Y-%m-%d')}")
        
        service = get_classroom_service(user_id)
        result = service.courses().courseWork().create(courseId=course_id, body=coursework_body).execute()
        print(f"Coursework created: {result}")
        coursework = result
        return coursework
    except Exception as e:
        return {"error": f"Failed to create coursework: {str(e)}"}
