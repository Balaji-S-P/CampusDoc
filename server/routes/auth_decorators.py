"""
Authentication decorators for Flask routes
"""
from functools import wraps
from flask import request, jsonify
from db_utils.db_helper import get_user


def auth_required(f):
    """
    Decorator that requires authentication.
    Checks if user_id is provided and validates it exists.
    
    The decorator will extract user_id from:
    - JSON body (data.get('user_id'))
    - Form data (request.form.get('user_id'))
    - URL parameters (request.args.get('user_id'))
    - URL path parameters (if function has user_id parameter)
    
    If user_id is not found or user doesn't exist, returns 401 Unauthorized.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = None
        
        # Try to get user_id from various sources
        if request.is_json:
            data = request.get_json() or {}
            user_id = data.get('user_id')
        
        if not user_id:
            user_id = request.form.get('user_id')
        
        if not user_id:
            user_id = request.args.get('user_id')
        
        # Check if user_id is in kwargs (from URL path)
        if not user_id and 'user_id' in kwargs:
            user_id = kwargs.get('user_id')
        
        if not user_id:
            return jsonify({"error": "Authentication required. user_id is missing."}), 401
        
        # Validate user exists
        user = get_user(user_id)
        if not user:
            return jsonify({"error": "Invalid user_id. User not found."}), 401
        
        # Add user_id to kwargs so the function can use it
        kwargs['authenticated_user_id'] = user_id
        kwargs['authenticated_user'] = user
        
        return f(*args, **kwargs)
    
    return decorated_function


def optional_auth(f):
    """
    Decorator that optionally validates authentication if user_id is provided.
    If user_id is provided, validates it exists. Otherwise, allows the request to proceed.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = None
        
        # Try to get user_id from various sources
        if request.is_json:
            data = request.get_json() or {}
            user_id = data.get('user_id')
        
        if not user_id:
            user_id = request.form.get('user_id')
        
        if not user_id:
            user_id = request.args.get('user_id')
        
        if not user_id and 'user_id' in kwargs:
            user_id = kwargs.get('user_id')
        
        # If user_id is provided, validate it
        if user_id:
            user = get_user(user_id)
            if not user:
                return jsonify({"error": "Invalid user_id. User not found."}), 401
            kwargs['authenticated_user_id'] = user_id
            kwargs['authenticated_user'] = user
        
        return f(*args, **kwargs)
    
    return decorated_function

