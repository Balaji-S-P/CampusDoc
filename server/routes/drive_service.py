from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
import requests
from googleapiclient.http import MediaIoBaseDownload,MediaFileUpload
import io
import os
from db_utils.db_helper import get_tokens, save_tokens

def get_drive_service(user_id):
    """user_id can be fetched using get_user_id(user_id) function
    """
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
    
    print(f"Credentials created, scopes: {creds.scopes}")
    return build('drive', 'v3', credentials=creds)


def download_file_from_drive_and_upload_to_gemini(file_id, user_id):
    """user_id can be fetched using get_user_id(user_id) function
    """
    try:
        service = get_drive_service(user_id)
        if isinstance(service, dict) and "error" in service:
            return service
            
        # Get file metadata first
        file_metadata = service.files().get(fileId=file_id).execute()
        file_name = file_metadata.get('name', 'downloaded_file')
        
        # Download the file content
        request = service.files().get_media(fileId=file_id)
        file_content = io.BytesIO()
        downloader = MediaIoBaseDownload(file_content, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
            print(f"Download {int(status.progress() * 100)}%.")
        
        file_content.seek(0)
        file_data = file_content.getvalue()
        from routes.ai_service import upload_to_gemini_from_bytes
        upload_result = upload_to_gemini_from_bytes(
            file_data, 
            file_name, 
            file_metadata.get('mimeType', 'application/octet-stream')
        )
        if upload_result["success"]:
            return {
                "success": True,
                "file_uri": upload_result.get("uri", ""),
                "file_name": file_name,
                "mime_type": file_metadata.get('mimeType', 'application/octet-stream'),
                "display_name": upload_result.get("display_name", file_name),
                "message": "File downloaded and uploaded to Gemini successfully"
            }
        else:
            return {"error": upload_result["error"]}
        
    except Exception as e:
        return {"error": f"Failed to download file from drive: {str(e)}"}

def upload_local_file_to_drive(file_path, user_id,mime_type):
    """user_id can be fetched using get_user_id(user_id) function
    """
    try:
        service = get_drive_service(user_id)
        if isinstance(service, dict) and "error" in service:
            return service
        mediafile=MediaFileUpload(file_path, mimetype=mime_type)
        # Upload to regular Drive folder instead of appDataFolder
        file=service.files().create(body={"name": os.path.basename(file_path)},media_body=mediafile,fields="id, webViewLink, webContentLink").execute()
        file_id=file.get("id")
        webViewLink=file.get("webViewLink")
        service.permissions().create(fileId=file_id,body={"role": "reader", "type": "anyone"}).execute()
        return {"success": True, "message": "File uploaded to drive successfully", "file_id": file_id, "webViewLink": webViewLink}
    except Exception as e:
        return {"error": f"Failed to upload file to drive: {str(e)}"}

