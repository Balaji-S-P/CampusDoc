from flask import Blueprint, request, jsonify
from datetime import datetime
from google import genai    
import os
from dotenv import load_dotenv

load_dotenv()
ai_service = Blueprint("ai_service", __name__)

# Initialize Gemini client directly
client = genai.Client(api_key=os.getenv('GOOGLE_API_KEY'))
def upload_to_gemini(file):
    try:
        import tempfile
        import os
        
        # Create a temporary file with the same extension
        file_ext = os.path.splitext(file.filename)[1] if file.filename else ''
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
            # Save the Flask file to the temporary file
            file.save(temp_file.name)
            temp_file_path = temp_file.name
        
        try:
            # Get file info
            file_name = file.filename or "uploaded_file"
            mime_type = file.content_type or "application/octet-stream"
            
            # Read file content
            with open(temp_file_path, 'rb') as f:
                file_content = f.read()
            
            # Upload file to Gemini Files API using the file content
            response = upload_to_gemini_from_bytes(file_content, file_name, mime_type)
            
            print(f"Upload response type: {type(response)}")
            print(f"Upload response: {response}")
            
            # Check if upload was successful
            if isinstance(response, dict) and "error" in response:
                # Upload failed, return error
                print(f"Upload failed: {response['error']}")
                return {
                    "success": False,
                    "error": response["error"]
                }
            else:
                # Upload successful, return file object with URI for further use
                print(f"Upload successful. File URI: {response.uri}")
                print(f"File display name: {response.display_name}")
                return {
                    "success": True,
                    "file": response,
                    "uri": response.uri,
                    "mime_type": response.mime_type,
                    "display_name": response.display_name
                }
        finally:
            # Clean up the temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to upload file: {str(e)}"
        }

def upload_to_gemini_from_bytes(file_content, file_name, mime_type):
    """Upload file content from bytes to Gemini Files API"""
    try:
        import tempfile
        import os
        
        # Create a temporary file with the correct extension
        file_ext = os.path.splitext(file_name)[1] if file_name else ''
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
            temp_file.write(file_content)
            temp_file_path = temp_file.name
        
        try:
            # Upload file to Gemini Files API using the file path
            response = client.files.upload(
                file=temp_file_path
            )
            
            # Return the same format as upload_to_gemini
            return {
                "success": True,
                "file": response,
                "uri": response.uri,
                "mime_type": response.mime_type,
                "display_name": response.display_name
            }
        finally:
            # Clean up the temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to upload file: {str(e)}"
        }

def summarize_file_from_gemini(file_uri, user_id):
    """Summarize a file that has been uploaded to Gemini"""
    try:
        # Create a prompt for summarization
        prompt = """
        Please provide a comprehensive summary of this document. Include:
        1. Main topics and themes
        2. Key points and important information
        3. Any important data, statistics, or facts
        4. Conclusions or recommendations if present
        5. Overall structure and organization
        
        Make the summary clear, well-organized, and informative.
        """
        file_part = genai.types.Part(file_data=genai.types.FileData(file_uri=file_uri))
        # Generate content using the uploaded file with proper format
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                prompt,
                file_part
            ]
        )
        
        if response and response.text:
            return {
                "success": True,
                "summary": response.text,
                "file_uri": file_uri
            }
        else:
            return {
                "success": False,
                "error": "No summary generated from the file"
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to summarize file: {str(e)}"
        }

def delete_file_from_gemini(file_uri):
    """Delete a file from Gemini Files API"""
    try:
        client.files.delete(file_uri)
        return {"success": True, "message": "File deleted successfully"}
    except Exception as e:
        return {"success": False, "error": f"Failed to delete file: {str(e)}"}