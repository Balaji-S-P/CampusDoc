from flask import Blueprint, request, jsonify
import os
import uuid
import json
from datetime import datetime
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import PyPDF2
import docx
import sqlite3
from PIL import Image
import pytesseract

file_service = Blueprint("file_service", __name__)

# Initialize the sentence transformer model
model = SentenceTransformer('all-MiniLM-L6-v2')

# Set default DATA_DIR if not provided
DATA_DIR = os.getenv("DATA_DIR", ".")
FILE_UPLOAD_FOLDER = os.path.join(DATA_DIR, "uploads")
USER_DIR = os.path.join(DATA_DIR, "users")
VECTOR_DB_DIR = os.path.join(DATA_DIR, "vector_dbs")
FOLDER_DB_PATH = os.path.join(DATA_DIR, "folders.db")

# Create directories if they don't exist
os.makedirs(FILE_UPLOAD_FOLDER, exist_ok=True)
os.makedirs(USER_DIR, exist_ok=True)
os.makedirs(VECTOR_DB_DIR, exist_ok=True)

def get_metadata_path(user_id):
    return os.path.join(USER_DIR, user_id, "metadata.jsonl")

def get_folder_metadata_path(user_id, folder_id):
    """Get metadata path for files in a specific folder"""
    folder_metadata_dir = os.path.join(USER_DIR, user_id, "folders", folder_id)
    os.makedirs(folder_metadata_dir, exist_ok=True)
    return os.path.join(folder_metadata_dir, "metadata.jsonl")

def get_folder_vector_db_path(user_id, folder_id):
    """Get the path for a folder's vector database"""
    return os.path.join(VECTOR_DB_DIR, f"{user_id}_{folder_id}.bin")

def extract_text_from_file(file_path, file_type):
    """Extract text content from various file types"""
    try:
        if file_type.lower() == '.pdf':
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page_num, page in enumerate(pdf_reader.pages):
                    page_text = page.extract_text()
                    if page_text.strip():  # If text extraction worked
                        text += page_text + "\n"
                    else:
                        # Try OCR for scanned pages
                        print(f"DEBUG: No text found on page {page_num + 1}, trying OCR...")
                        try:
                            # Convert PDF page to image and use OCR
                            import pdf2image
                            images = pdf2image.convert_from_path(file_path, first_page=page_num + 1, last_page=page_num + 1)
                            if images:
                                ocr_text = pytesseract.image_to_string(images[0])
                                if ocr_text.strip():
                                    text += ocr_text + "\n"
                                    print(f"DEBUG: OCR extracted {len(ocr_text)} characters from page {page_num + 1}")
                        except Exception as ocr_error:
                            print(f"DEBUG: OCR failed for page {page_num + 1}: {ocr_error}")
                            if "poppler" in str(ocr_error).lower():
                                print("DEBUG: Poppler not installed. To enable OCR for scanned PDFs, install Poppler:")
                                print("DEBUG: macOS: brew install poppler")
                                print("DEBUG: Ubuntu: sudo apt-get install poppler-utils")
                return text
        elif file_type.lower() in ['.doc', '.docx']:
            doc = docx.Document(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text
        elif file_type.lower() == '.txt':
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        else:
            # For other file types, try to read as text
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                return file.read()
    except Exception as e:
        print(f"Error extracting text from {file_path}: {str(e)}")
        return ""

def add_to_vector_db(user_id, folder_id, file_id, text_content):
    """Add text content to the folder's vector database"""
    try:
        print(f"DEBUG: add_to_vector_db called with text length: {len(text_content)}")
        vector_db_path = get_folder_vector_db_path(user_id, folder_id)
        metadata_path = get_folder_metadata_path(user_id, folder_id)
        
        # Load existing index or create new one
        if os.path.exists(vector_db_path):
            index = faiss.read_index(vector_db_path)
        else:
            dimension = 384  # all-MiniLM-L6-v2 output size
            index = faiss.IndexFlatL2(dimension)
        
        # Split text into chunks (you can adjust chunk size)
        chunk_size = 1000
        chunks = [text_content[i:i+chunk_size] for i in range(0, len(text_content), chunk_size)]
        print(f"DEBUG: Created {len(chunks)} chunks from text")
        
        # Generate embeddings for each chunk
        embeddings = model.encode(chunks)
        print(f"DEBUG: Generated embeddings shape: {embeddings.shape}")
        
        # Add embeddings to the index
        index.add(embeddings.astype('float32'))
        
        # Save the updated index
        faiss.write_index(index, vector_db_path)
        
        # Save chunk metadata to the metadata file
        print(f"DEBUG: Saving {len(chunks)} chunk metadata entries")
        for i, chunk_text in enumerate(chunks):
            chunk_metadata = {
                "file_id": file_id,
                "chunk_index": i,
                "chunk_text": chunk_text,
                "user_id": user_id,
                "folder_id": folder_id,
                "created_at": datetime.now().isoformat()
            }
            
            # Append chunk metadata to the metadata file
            with open(metadata_path, "a") as f:
                f.write(json.dumps(chunk_metadata) + "\n")
        
        print(f"DEBUG: Successfully saved chunk metadata to {metadata_path}")
        
        return len(chunks)
        
    except Exception as e:
        print(f"Error adding to vector database: {str(e)}")
        return 0

def update_folder_file_count(user_id, folder_id,file_count):
    """Update the file count for a folder"""
    try:
        conn = sqlite3.connect(FOLDER_DB_PATH)
        cursor = conn.cursor()
        
        # Count files in the folder
            
        # Update the file count in the database
        cursor.execute('''
            SELECT file_count FROM folders 
            WHERE folder_id = ? AND user_id = ?
        ''', (folder_id, user_id))
        file_count = cursor.fetchone()[0] + file_count  
        cursor.execute('''
            UPDATE folders 
            SET file_count = ? 
            WHERE folder_id = ? AND user_id = ?
        ''', (file_count, folder_id, user_id))
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        print(f"Error updating folder file count: {str(e)}")

@file_service.route("/upload/<user_id>", methods=["POST"])
def upload_file(user_id):
    try:
        # Check if this is a folder-based upload
        folder_id = request.form.get('folder_id')
        
        if folder_id:
            # Folder-based upload
            return upload_to_folder(user_id, folder_id)
        else:
            # Regular upload (existing functionality)
            return upload_to_general(user_id)
        
    except Exception as e:
        return jsonify({"error": f"Upload failed: {str(e)}"}), 500

def upload_to_folder(user_id, folder_id):
    """Upload files to a specific folder"""
    try:
        # Verify folder exists and belongs to user
        conn = sqlite3.connect(FOLDER_DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT folder_name FROM folders 
            WHERE folder_id = ? AND user_id = ?
        ''', (folder_id, user_id))
        
        folder_info = cursor.fetchone()
        if not folder_info:
            conn.close()
            return jsonify({"error": "Folder not found"}), 404
        
        conn.close()
        
        # Create folder directory structure
        folder_dir = os.path.join(FILE_UPLOAD_FOLDER, user_id, "folders", folder_id)
        os.makedirs(folder_dir, exist_ok=True) 
        
        uploaded_files = []

        file_keys = [key for key in request.files.keys() if key.startswith('file_')]
        
        for file_key in file_keys:
            file = request.files[file_key]
            if file.filename == '':
                continue
                
            file_id = str(uuid.uuid4())
            file_name = file_id + "_" + file.filename
            CREATED_AT = datetime.now().isoformat()
            file_path = os.path.join(folder_dir, file_name)
            
            # Save file
            file.save(file_path)
            
            # Extract text content for vector database
            file_extension = os.path.splitext(file.filename)[1]
            text_content = extract_text_from_file(file_path, file_extension)
            print(f"DEBUG: Extracted text length: {len(text_content)} for file {file.filename}")
            print(f"DEBUG: First 200 chars: {text_content[:200]}")
            
            # Add to vector database
            chunk_count = 0
            if text_content.strip():
                chunk_count = add_to_vector_db(user_id, folder_id, file_id, text_content)
                print(f"DEBUG: Created {chunk_count} chunks for file {file.filename}")
            else:
                print(f"DEBUG: No text content extracted from {file.filename}")
            
            # Save metadata
            metadata = {
                "file_id": file_id, 
                "file_name": file_name, 
                "original_name": file.filename,
                "user_id": user_id, 
                "folder_id": folder_id,
                "created_at": CREATED_AT,
                "file_size": os.path.getsize(file_path),
                "chunk_count": chunk_count
            }
            
            # Save to folder-specific metadata
            folder_metadata_path = get_folder_metadata_path(user_id, folder_id)
            with open(folder_metadata_path, "a") as f:
                f.write(json.dumps(metadata) + "\n")
            
            uploaded_files.append(metadata)
        
        # Update folder file count
            update_folder_file_count(user_id, folder_id,len(uploaded_files))
        
        return jsonify({
            "message": f"Successfully uploaded {len(uploaded_files)} files to folder",
            "files": uploaded_files,
            "folder_id": folder_id,
            "folder_name": folder_info[0]
        })
        
    except Exception as e:
        return jsonify({"error": f"Folder upload failed: {str(e)}"}), 500

def upload_to_general(user_id):
    """Upload files to general user directory (existing functionality)"""
    try:
        # Create user directory if it doesn't exist
        user_dir = os.path.join(FILE_UPLOAD_FOLDER, user_id)
        os.makedirs(user_dir, exist_ok=True)
        
        # Create user metadata directory
        user_metadata_dir = os.path.join(USER_DIR, user_id)
        os.makedirs(user_metadata_dir, exist_ok=True)
        
        uploaded_files = []
        file_keys = [key for key in request.files.keys() if key.startswith('file_')]
        
        for file_key in file_keys:
            file = request.files[file_key]
            if file.filename == '':
                continue
                
            file_id = str(uuid.uuid4())
            file_name = file_id + "_" + file.filename
            CREATED_AT = datetime.now().isoformat()
            
            # Save file
            file.save(os.path.join(user_dir, file_name))
            
            # Save metadata
            metadata = {
                "file_id": file_id, 
                "file_name": file_name, 
                "original_name": file.filename,
                "user_id": user_id, 
                "created_at": CREATED_AT,
                "file_size": os.path.getsize(os.path.join(user_dir, file_name))
            }
            
            with open(get_metadata_path(user_id), "a") as f:
                f.write(json.dumps(metadata) + "\n")
            
            uploaded_files.append(metadata)
        
        return jsonify({
            "message": f"Successfully uploaded {len(uploaded_files)} files",
            "files": uploaded_files
        })
        
    except Exception as e:
        return jsonify({"error": f"Upload failed: {str(e)}"}), 500

@file_service.route("/get_files/<user_id>", methods=["GET"])
def get_files(user_id):
    try:
        files = []
        metadata_path = get_metadata_path(user_id)
        
        if os.path.exists(metadata_path):
            with open(metadata_path, "r") as f:
                for line in f:
                    if line.strip():  # Skip empty lines
                        metadata = json.loads(line)
                        files.append({
                            "file_id": metadata["file_id"], 
                            "file_name": metadata["file_name"],
                            "original_name": metadata.get("original_name", metadata["file_name"]),
                            "created_at": metadata["created_at"],
                            "file_size": metadata.get("file_size", 0)
                        })
        
        return jsonify({"files": files, "user_id": user_id})
        
    except Exception as e:
        return jsonify({"error": f"Failed to get files: {str(e)}"}), 500

@file_service.route("/delete_file/<user_id>/<file_id>", methods=["DELETE"])
def delete_file(user_id, file_id):
    try:
        metadata_path = get_metadata_path(user_id)
        file_name = None
        
        if not os.path.exists(metadata_path):
            return jsonify({"error": "No files found for user"}), 404
        
        # Read and filter metadata
        with open(metadata_path, "r") as f:
            lines = f.readlines()
        
        with open(metadata_path, "w") as f:
            for line in lines:
                if line.strip():  # Skip empty lines
                    metadata = json.loads(line)
                    if metadata["file_id"] != file_id:
                        f.write(line)
                    else:
                        file_name = metadata["file_name"]
        
        if file_name:
            # Delete the actual file
            file_path = os.path.join(FILE_UPLOAD_FOLDER, user_id, file_name)
            if os.path.exists(file_path):
                os.remove(file_path)
            
            return jsonify({
                "message": "File deleted successfully", 
                "user_id": user_id, 
                "file_name": file_name
            })
        else:
            return jsonify({"error": "File not found"}), 404
            
    except Exception as e:
        return jsonify({"error": f"Failed to delete file: {str(e)}"}), 500

