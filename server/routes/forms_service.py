from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
import requests
from db_utils.db_helper import get_tokens, save_tokens
from .drive_service import get_drive_service

def get_forms_service(user_id):
    tokens = get_tokens(user_id)
    if not tokens:
        return {"error": "No tokens found for user"}
    creds = Credentials(
        token=tokens['access_token'],
        refresh_token=tokens['refresh_token'],
        token_uri=tokens.get('token_uri', 'https://oauth2.googleapis.com/token'),
        client_id=tokens.get('client_id'),
        client_secret=tokens.get('client_secret'),
        scopes=tokens['scopes']
    )
    
    # Refresh the credentials if needed
    if creds.expired and creds.refresh_token:
        print("Credentials expired, refreshing...")
        creds.refresh(requests.Request())
        print("Credentials refreshed successfully")
        
        # Save the refreshed tokens back to the database
        try:
            save_tokens(user_id, creds, tokens.get('email', ''))
            print("Refreshed tokens saved to database")
        except Exception as e:
            print(f"Warning: Could not save refreshed tokens: {e}")
    
    return build('forms', 'v1', credentials=creds)

def create_quiz(user_id, quiz_name, quiz_description, quiz_questions):
    """
    [
        {
            "question": "What is the capital of France?",
            "options": [{"value":"Paris"}, {"value":"London"}, {"value":"Berlin"}, {"value":"Madrid"}],
            "isRequired": true,
            "type": "RADIO",
            "pointValue": 1,
            "correctAnswers": {"answers": [{"value":"Paris"}]}
        },
        {
            "question": "What is the capital of Germany?",
            "options": [{"value":"Berlin"}, {"value":"Munich"}, {"value":"Hamburg"}, {"value":"Frankfurt"}],
            "isRequired": true,
            "type": "RADIO",
            "pointValue": 1,
            "correctAnswers": {"answers": [{"value":"Berlin"}]}
        }
    ]
    type: RADIO, CHECKBOX, DROPDOWN
     """
    # Step 1: Create the form with just the title
    create_body = {
        'info': {
            'title': quiz_name,
        }
    }
    
    service = get_forms_service(user_id)
    quiz = service.forms().create(body=create_body).execute()
    form_id = quiz['formId']
    
    # Step 2: Use batchUpdate to add questions and settings
    requests = []
    
    # Add quiz settings
    requests.append({
        'updateSettings': {
            'settings': {
                'quizSettings': {
                    'isQuiz': True
                }
            },
            'updateMask': 'quizSettings.isQuiz'
        }
    })
    
    # Add questions
    for i, question in enumerate(quiz_questions):
        # Map question types to valid Google Forms types
        question_type = question['type']
        if question_type == 'RADIO':
            choice_type = 'RADIO'
        elif question_type == 'CHECKBOX':
            choice_type = 'CHECKBOX'
        elif question_type == 'DROPDOWN':
            choice_type = 'DROP_DOWN'
        else:
            choice_type = 'RADIO'  # Default to RADIO
        
        item = {
            "title": question['question'],
            "questionItem": {
                "question": {
                    "required": question['isRequired'],
                    "choiceQuestion": {
                        "type": choice_type,
                        "options": question['options']
                    },
                    "grading": {
                        "pointValue": question['pointValue'],
                        "correctAnswers": question['correctAnswers']
                    }
                }
            }
        }
        
        requests.append({
            'createItem': {
                'item': item,
                'location': {
                    'index': i
                }
            }
        })
    
    # Execute batch update
    batch_update_body = {
        'requests': requests
    }
    
    service.forms().batchUpdate(formId=form_id, body=batch_update_body).execute()
    
    # Return the updated form
    return service.forms().get(formId=form_id).execute()

def list_forms(user_id):
    """user_id can be fetched using get_user_id(user_id) function
    """
    drive_service = get_drive_service(user_id)
    results = drive_service.files().list(
        q="mimeType='application/vnd.google-apps.form' and trashed=false",
        fields="files(id, name, webViewLink, createdTime, modifiedTime)"
    ).execute()
    return results.get("files", [])

def get_form(user_id, form_id):
    """user_id can be fetched using get_user_id(user_id) function
    form_id can be fetched using list_forms(user_id) function
    return form object
    """
    drive_service = get_drive_service(user_id)
    result = drive_service.files().get(fileId=form_id).execute()
    return result

def list_form_responses(user_id, form_id):
    """user_id can be fetched using get_user_id(user_id) function
    form_id can be fetched using list_forms(user_id) function
    return list of response objects
    """
    service = get_forms_service(user_id)
    result = service.forms().responses().list(formId=form_id).execute()
    return result

def get_form_response(user_id, form_id, response_id):
    """user_id can be fetched using get_user_id(user_id) function
    form_id can be fetched using list_forms(user_id) function
    response_id can be fetched using list_form_responses(user_id, form_id) function
    """
    service = get_forms_service(user_id)
    result = service.forms().responses().get(formId=form_id, responseId=response_id).execute()
    return result