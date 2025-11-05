from flask import Blueprint, request, jsonify
from db_utils.db_helper import get_tokens, save_tokens
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import session
import requests
import markdown
import re
from .classroom_service import list_courses, list_course_students, list_student_submissions, get_coursework, get_student, get_coursework_materials, list_courseworks
from .drive_service import download_file_from_drive_and_upload_to_gemini
from .ai_service import summarize_file_from_gemini
from .forms_service import create_quiz, list_forms, get_form, list_form_responses, get_form_response
from .classroom_service import create_announcement, create_coursework
from .pdf_service import question_bank_generator, answer_key_generator
def get_email_service(user_id):
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
    service = build('gmail', 'v1', credentials=creds)
    print(f"Service object type: {type(service)}")
    print(f"Service has users method: {hasattr(service, 'users')}")
    
    return service

def preprocess_latex(text):
    """Pre-process LaTeX syntax to make it email-friendly"""
    import re
    
    # Handle LaTeX matrices - convert to HTML tables
    matrix_pattern = r'\\begin\{pmatrix\}(.*?)\\end\{pmatrix\}'
    
    def replace_matrix(match):
        matrix_content = match.group(1)
        # Split by \\ to get rows
        rows = [row.strip() for row in matrix_content.split('\\\\') if row.strip()]
        
        # Convert each row to HTML table row
        html_rows = []
        for row in rows:
            # Split by & to get cells
            cells = [cell.strip() for cell in row.split('&')]
            html_cells = ''.join([f'<td>{cell}</td>' for cell in cells])
            html_rows.append(f'<tr>{html_cells}</tr>')
        
        # Create HTML table
        table_html = f'<table class="matrix-table"><tbody>{"".join(html_rows)}</tbody></table>'
        return table_html
    
    # Replace matrices
    text = re.sub(matrix_pattern, replace_matrix, text, flags=re.DOTALL)
    
    # Handle other LaTeX math expressions - convert to plain text
    # Remove $$ delimiters
    text = re.sub(r'\$\$(.*?)\$\$', r'\1', text, flags=re.DOTALL)
    
    # Remove single $ delimiters
    text = re.sub(r'\$(.*?)\$', r'\1', text, flags=re.DOTALL)
    
    # Handle LaTeX commands - convert common ones to readable text
    latex_commands = {
        r'\\begin\{.*?\}': '',
        r'\\end\{.*?\}': '',
        r'\\\\': '<br>',
        r'\\&': '&',
        r'\\%': '%',
        r'\\#': '#',
        r'\\_': '_',
        r'\\{': '{',
        r'\\}': '}',
    }
    
    for pattern, replacement in latex_commands.items():
        text = re.sub(pattern, replacement, text)
    
    return text

def convert_markdown_to_html(markdown_text):
    """Convert markdown text to HTML for email display"""
    try:
        # Pre-process LaTeX syntax to make it email-friendly
        processed_text = preprocess_latex(markdown_text)
        
        # Configure markdown with extensions for better email formatting
        md = markdown.Markdown(extensions=[
            'markdown.extensions.extra',
            'markdown.extensions.codehilite',
            'markdown.extensions.tables',
            'markdown.extensions.toc'
        ])
        
        # Convert markdown to HTML
        html_content = md.convert(processed_text)
        
        # Add basic CSS styling for better email appearance
        styled_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                h1, h2, h3, h4, h5, h6 {{
                    color: #2c3e50;
                    margin-top: 20px;
                    margin-bottom: 10px;
                }}
                code {{
                    background-color: #f4f4f4;
                    padding: 2px 4px;
                    border-radius: 3px;
                    font-family: 'Courier New', monospace;
                }}
                pre {{
                    background-color: #f4f4f4;
                    padding: 10px;
                    border-radius: 5px;
                    overflow-x: auto;
                }}
                blockquote {{
                    border-left: 4px solid #ddd;
                    margin: 0;
                    padding-left: 20px;
                    color: #666;
                }}
                table {{
                    border-collapse: collapse;
                    width: 100%;
                    margin: 10px 0;
                }}
                th, td {{
                    border: 1px solid #ddd;
                    padding: 8px;
                    text-align: left;
                }}
                th {{
                    background-color: #f2f2f2;
                }}
                .matrix-table {{
                    border: 2px solid #333;
                    margin: 15px auto;
                    text-align: center;
                }}
                .matrix-table td {{
                    border: 1px solid #333;
                    padding: 10px;
                    font-family: 'Courier New', monospace;
                    font-weight: bold;
                }}
                ul, ol {{
                    padding-left: 20px;
                }}
                a {{
                    color: #3498db;
                    text-decoration: none;
                }}
                a:hover {{
                    text-decoration: underline;
                }}
            </style>
        </head>
        <body>
            {html_content}
        </body>
        </html>
        """
        
        return styled_html
    except Exception as e:
        print(f"Error converting markdown to HTML: {e}")
        # Fallback to plain text if conversion fails
        return f"<html><body><pre>{markdown_text}</pre></body></html>"

def is_markdown_content(text):
    """Check if the text contains markdown formatting or LaTeX syntax"""
    markdown_patterns = [
        r'^#{1,6}\s+',  # Headers
        r'\*\*.*?\*\*',  # Bold
        r'\*.*?\*',      # Italic
        r'`.*?`',        # Inline code
        r'```.*?```',    # Code blocks
        r'^\s*[-*+]\s+', # Lists
        r'^\s*\d+\.\s+', # Numbered lists
        r'^\s*>\s+',     # Blockquotes
        r'\[.*?\]\(.*?\)', # Links
        r'^\|.*\|$',     # Tables
        # LaTeX patterns
        r'\$\$.*?\$\$',  # LaTeX display math
        r'\$.*?\$',      # LaTeX inline math
        r'\\begin\{.*?\}', # LaTeX environments
        r'\\end\{.*?\}',   # LaTeX environments
        r'\\[a-zA-Z]+\{.*?\}', # LaTeX commands
    ]
    
    for pattern in markdown_patterns:
        if re.search(pattern, text, re.MULTILINE | re.DOTALL):
            return True
    return False

def send_email(to, subject, message, user_id=None):
    """Send an email to the user with markdown support"""
    try:
        print(f"send_email called with user_id: me")
        service = get_email_service(user_id)
        
        # Check if service.users() exists
        users_resource = service.users()
        print(f"Users resource type: {type(users_resource)}")
        print(f"Users resource has sendMessage: {hasattr(users_resource, 'sendMessage')}")
        print(f"Available methods on users_resource: {dir(users_resource)}")
        
        # Check if the message contains markdown formatting
        if is_markdown_content(message):
            print("Markdown content detected, converting to HTML email")
            # Create multipart email with both HTML and plain text
            email_message = MIMEMultipart('alternative')
            
            # Create plain text version (strip markdown formatting)
            plain_text = re.sub(r'#{1,6}\s+', '', message)  # Remove headers
            plain_text = re.sub(r'\*\*(.*?)\*\*', r'\1', plain_text)  # Remove bold
            plain_text = re.sub(r'\*(.*?)\*', r'\1', plain_text)  # Remove italic
            plain_text = re.sub(r'`(.*?)`', r'\1', plain_text)  # Remove inline code
            plain_text = re.sub(r'```.*?```', '', plain_text, flags=re.DOTALL)  # Remove code blocks
            plain_text = re.sub(r'^\s*[-*+]\s+', '- ', plain_text, flags=re.MULTILINE)  # Convert lists
            plain_text = re.sub(r'^\s*\d+\.\s+', '1. ', plain_text, flags=re.MULTILINE)  # Convert numbered lists
            plain_text = re.sub(r'^\s*>\s+', '', plain_text, flags=re.MULTILINE)  # Remove blockquotes
            plain_text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', plain_text)  # Remove link formatting
            
            # Create HTML version
            html_content = convert_markdown_to_html(message)
            
            # Attach both versions
            part1 = MIMEText(plain_text, 'plain', 'utf-8')
            part2 = MIMEText(html_content, 'html', 'utf-8')
            
            email_message.attach(part1)
            email_message.attach(part2)
        else:
            print("Plain text content, creating simple text email")
            # Create simple text email
            email_message = MIMEText(message, 'plain', 'utf-8')
        
        # Set email headers
        email_message['To'] = to
        email_message['Subject'] = subject
        email_message['From'] = ''
        
        # Encode the email
        raw = base64.urlsafe_b64encode(email_message.as_bytes()).decode()
        
        print("Attempting to send email...")
        # Try the correct method name - it should be 'messages' not 'sendMessage'
        messages_resource = users_resource.messages()
        print(f"Messages resource type: {type(messages_resource)}")
        print(f"Messages resource has send: {hasattr(messages_resource, 'send')}")
        result = messages_resource.send(userId="me", body={"raw": raw}).execute()
        print(f"Email sent successfully: {result}")
        return {'message': 'Email sent successfully'}
    except Exception as e:
        print(f"Error in send_email: {e}")
        print(f"Error type: {type(e)}")
        return {'error': str(e)}

def handle_part(part, user_id=None):
    if not part or not part.function_call:
        return
    available_functions={
        "send_email": send_email,
        "list_courses": list_courses,
        "list_course_students": list_course_students,
        "list_student_submissions": list_student_submissions,
        "get_coursework": get_coursework,
        "get_student": get_student,
        "get_coursework_materials": get_coursework_materials,
        "list_courseworks": list_courseworks,
        "download_file_from_drive_and_upload_to_gemini": download_file_from_drive_and_upload_to_gemini,
        "summarize_file_from_gemini": summarize_file_from_gemini,
        "create_quiz": create_quiz,
        "create_announcement": create_announcement,
        "list_forms": list_forms,
        "get_form": get_form,
        "list_form_responses": list_form_responses,
        "get_form_response": get_form_response,
        "question_bank_generator": question_bank_generator,
        "create_coursework": create_coursework,
        "answer_key_generator": answer_key_generator
    }
    if part.function_call.name in available_functions:
        response=available_functions[part.function_call.name](**part.function_call.args, user_id=user_id)
        return response
    else:
        print(f"Function {part.function_call.name} not found")
        return None