from flask import Blueprint, redirect, request, session, jsonify
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
import os
import json
from dotenv import load_dotenv
from db_utils.db_helper import create_user, get_user_id, user_exists, save_tokens, get_user

load_dotenv()
from routes.email_service import get_email_service
auth_bp = Blueprint('auth', __name__)
# Only allow insecure transport in development - use environment variable
if os.getenv("ENV") != "production":
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

@auth_bp.route("/authorize")
def authorize():
    user_id = request.args.get("user_id")
    credentials_file = os.getenv("GOOGLE_OAUTH_CREDENTIALS_FILE", "credentials.json")
    redirect_uri = os.getenv("OAUTH_REDIRECT_URI", "http://localhost:5001/api/auth/oauth2callback")
    flow = Flow.from_client_secrets_file(
        credentials_file,
        scopes=[ "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",

    # Classroom
    "https://www.googleapis.com/auth/classroom.courses.readonly",
    "https://www.googleapis.com/auth/classroom.rosters.readonly",
    "https://www.googleapis.com/auth/classroom.student-submissions.me.readonly",
    "https://www.googleapis.com/auth/classroom.student-submissions.students.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/drive.file",
      "https://www.googleapis.com/auth/forms.body",
    "https://www.googleapis.com/auth/forms.responses.readonly",
    "https://www.googleapis.com/auth/classroom.announcements",
    "https://www.googleapis.com/auth/classroom.coursework.students"
    ]        ,
        redirect_uri=redirect_uri,
    )
    session["user_id"] = user_id
    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true"
    )
    session["state"] = state
    return redirect(authorization_url)

@auth_bp.route("/oauth2callback")
def oauth2callback():
    state = session["state"]
    credentials_file = os.getenv("GOOGLE_OAUTH_CREDENTIALS_FILE", "credentials.json")
    redirect_uri = os.getenv("OAUTH_REDIRECT_URI", "http://localhost:5001/api/auth/oauth2callback")
    flow = Flow.from_client_secrets_file(
        credentials_file,
        scopes=[ "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",

    # Classroom
    "https://www.googleapis.com/auth/classroom.courses.readonly",
    "https://www.googleapis.com/auth/classroom.rosters.readonly",
    "https://www.googleapis.com/auth/classroom.student-submissions.me.readonly",
    "https://www.googleapis.com/auth/classroom.student-submissions.students.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/drive.file",
      "https://www.googleapis.com/auth/forms.body",
    "https://www.googleapis.com/auth/forms.responses.readonly",
    "https://www.googleapis.com/auth/classroom.announcements",
    "https://www.googleapis.com/auth/classroom.coursework.students"],
        state=state,
        redirect_uri=redirect_uri,
    )
    flow.fetch_token(authorization_response=request.url)
    creds = flow.credentials

    user_id = session["user_id"]
    # Save tokens to DB for that user_id (like before)
    
    # Extract serializable parts of credentials
    creds_data = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": creds.scopes,
        "expiry": creds.expiry.isoformat() if creds.expiry else None
    }
    # Save credentials to file (creds.json is in .gitignore)
    creds_file = os.getenv("GOOGLE_OAUTH_CREDS_FILE", "creds.json")
    print(f"Saving credentials to {creds_file}")
    with open(creds_file, "w") as f:
        json.dump(creds_data, f, indent=2)
    
    # Get user's email from Google API
    try:
        service = build('gmail', 'v1', credentials=creds)
        profile = service.users().getProfile(userId="me").execute()
        email = profile.get('emailAddress')
        
        if not email:
            return "❌ Could not retrieve email address from Google"
            
        # Check if user exists, if not create them
        
        # Get the user_id for the email
        user_id = get_user_id(email)
        save_tokens(user_id, creds, email=email)
    
            
    except Exception as e:
        return f"❌ Error getting user email: {str(e)}"

    return "✅ Gmail connected successfully! You can close this tab."

@auth_bp.route('/login', methods=['POST'])
def login():
    """User login endpoint"""
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        
        if not email or not password:
            return jsonify({"error": "Email and password are required"}), 400
        user_id = get_user_id(email)
        user = get_user(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        if user[2] != password:
            return jsonify({"error": "Invalid credentials"}), 401
        # Simple authentication logic - replace with your actual auth
        
        return jsonify({
            "message": "Login successful",
            "user_id": user[0],
            "email": user[1],
            "role": user[2]
        })
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@auth_bp.route('/register', methods=['POST'])
def register():
    """User registration endpoint"""
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        role = data.get('role', 'student')
        if user_exists(email):
            return jsonify({"error": "User already exists"}), 400
        if not email :
            return jsonify({"error": "Email is required"}), 400
        
        # Generate user ID
        create_user(email, password, role)
        user_id = get_user_id(email)
        return jsonify({
            "message": "Registration successful",
            "user_id": user_id,
            "email": email,
            "role": role
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@auth_bp.route('/profile', methods=['GET'])
def get_profile():
    """Get user profile"""
    try:
        user_id = request.args.get('user_id')
        
        if not user_id:
            return jsonify({"error": "user_id is required"}), 400
        
        # Return mock profile data
        return jsonify({
            "user_id": user_id,
            "name": "John Doe",
            "email": "john@skcet.ac.in",
            "role": "student",
            "department": "CSE",
            "year": "3rd Year"
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500