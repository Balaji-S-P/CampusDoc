"""
Flask Application Factory with Blueprint Registration
"""

from flask import Flask
from flask_cors import CORS
import os
from dotenv import load_dotenv
from .authorization import auth_bp
from db_utils.db_helper import init_db
from .file_service import file_service
from .folder_service import folder_service
# Load environment variables
load_dotenv()

def create_app():
    """Application factory function"""
    app = Flask(__name__)
    init_db()
    # Configure CORS for external access
    CORS(app, origins=[
        "http://localhost:5173",  # Local development
        "https://localhost:5173", # Local development with HTTPS
        "https://*.ngrok.io",     # Any ngrok subdomain
        "https://*.ngrok-free.app", # New ngrok domains
        "https://*.ngrok.app"     # Alternative ngrok domains
    ], supports_credentials=True)
    
    # Register blueprints
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(file_service, url_prefix='/api/file')
    app.register_blueprint(folder_service, url_prefix='/api')
    return app
