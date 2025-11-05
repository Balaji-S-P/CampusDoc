from flask import Blueprint, request, jsonify
import os
import uuid
import json
import sqlite3
from datetime import datetime
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

folder_service = Blueprint("folder_service", __name__)

# Set default DATA_DIR if not provided
DATA_DIR = os.getenv("DATA_DIR", ".")
FOLDER_DB_PATH = os.path.join(DATA_DIR, "folders.db")
VECTOR_DB_DIR = os.path.join(DATA_DIR, "vector_dbs")

# Create directories if they don't exist
os.makedirs(VECTOR_DB_DIR, exist_ok=True)

# Initialize the sentence transformer model
model = SentenceTransformer('all-MiniLM-L6-v2')

def init_folder_db():
    """Initialize the folder database"""
    conn = sqlite3.connect(FOLDER_DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS folders (
            folder_id TEXT PRIMARY KEY,
            folder_name TEXT NOT NULL,
            user_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            vector_db_name TEXT NOT NULL,
            file_count INTEGER DEFAULT 0
        )
    ''')
    
    conn.commit()
    conn.close()

def get_folder_vector_db_path(user_id, folder_id):
    """Get the path for a folder's vector database"""
    return os.path.join(VECTOR_DB_DIR, f"{user_id}_{folder_id}.bin")

def create_vector_db(folder_id, user_id):
    """Create a new FAISS vector database for a folder"""
    vector_db_path = get_folder_vector_db_path(user_id, folder_id)
    
    # Create a new FAISS index with 384 dimensions (all-MiniLM-L6-v2 output size)
    dimension = 384
    index = faiss.IndexFlatL2(dimension)
    
    # Save the empty index
    faiss.write_index(index, vector_db_path)
    
    return vector_db_path

@folder_service.route("/folders/<user_id>", methods=["GET"])
def get_folders(user_id):
    """Get all folders for a user"""
    try:
        init_folder_db()
        conn = sqlite3.connect(FOLDER_DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT folder_id, folder_name, created_at, vector_db_name, file_count
            FROM folders 
            WHERE user_id = ?
            ORDER BY created_at DESC
        ''', (user_id,))
        
        folders = []
        for row in cursor.fetchall():
            folders.append({
                "folder_id": row[0],
                "folder_name": row[1],
                "created_at": row[2],
                "vector_db_name": row[3],
                "file_count": row[4]
            })
        
        conn.close()
        return jsonify({"folders": folders})
        
    except Exception as e:
        return jsonify({"error": f"Failed to get folders: {str(e)}"}), 500

@folder_service.route("/folders/<user_id>", methods=["POST"])
def create_folder(user_id):
    """Create a new folder for a user"""
    try:
        data = request.get_json()
        folder_name = data.get("folder_name")
        
        if not folder_name or not folder_name.strip():
            return jsonify({"error": "Folder name is required"}), 400
        
        folder_name = folder_name.strip()
        
        # Check if folder name already exists for this user
        init_folder_db()
        conn = sqlite3.connect(FOLDER_DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT folder_id FROM folders 
            WHERE user_id = ? AND folder_name = ?
        ''', (user_id, folder_name))
        
        if cursor.fetchone():
            conn.close()
            return jsonify({"error": "Folder name already exists"}), 400
        
        # Create new folder
        folder_id = str(uuid.uuid4())
        created_at = datetime.now().isoformat()
        vector_db_name = f"{user_id}_{folder_id}"
        
        # Create the vector database
        create_vector_db(folder_id, user_id)
        
        # Insert folder into database
        cursor.execute('''
            INSERT INTO folders (folder_id, folder_name, user_id, created_at, vector_db_name, file_count)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (folder_id, folder_name, user_id, created_at, vector_db_name, 0))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            "message": "Folder created successfully",
            "folder": {
                "folder_id": folder_id,
                "folder_name": folder_name,
                "user_id": user_id,
                "created_at": created_at,
                "vector_db_name": vector_db_name,
                "file_count": 0
            }
        })
        
    except Exception as e:
        return jsonify({"error": f"Failed to create folder: {str(e)}"}), 500

@folder_service.route("/folders/<user_id>/<folder_id>", methods=["DELETE"])
def delete_folder(user_id, folder_id):
    """Delete a folder and its associated vector database"""
    try:
        init_folder_db()
        conn = sqlite3.connect(FOLDER_DB_PATH)
        cursor = conn.cursor()
        
        # Get folder info before deletion
        cursor.execute('''
            SELECT folder_name, vector_db_name FROM folders 
            WHERE folder_id = ? AND user_id = ?
        ''', (folder_id, user_id))
        
        folder_info = cursor.fetchone()
        if not folder_info:
            conn.close()
            return jsonify({"error": "Folder not found"}), 404
        
        # Delete folder from database
        cursor.execute('''
            DELETE FROM folders 
            WHERE folder_id = ? AND user_id = ?
        ''', (folder_id, user_id))
        
        conn.commit()
        conn.close()
        
        # Delete vector database file
        vector_db_path = get_folder_vector_db_path(user_id, folder_id)
        if os.path.exists(vector_db_path):
            os.remove(vector_db_path)
        
        return jsonify({
            "message": "Folder deleted successfully",
            "folder_id": folder_id,
            "folder_name": folder_info[0]
        })
        
    except Exception as e:
        return jsonify({"error": f"Failed to delete folder: {str(e)}"}), 500

@folder_service.route("/folders/<user_id>/<folder_id>/files", methods=["GET"])
def get_folder_files(user_id, folder_id):
    """Get all files in a specific folder"""
    try:
        # Check if folder exists
        init_folder_db()
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
        
        # Get files from the folder's metadata file
        folder_metadata_path = os.path.join(DATA_DIR, "users", user_id, "folders", folder_id, "metadata.jsonl")
        files = []
        
        if os.path.exists(folder_metadata_path):
            with open(folder_metadata_path, "r") as f:
                for line in f:
                    if line.strip():
                        metadata = json.loads(line)
                        # Only process file-level metadata (has file_name field)
                        if "file_name" in metadata:
                            files.append({
                                "file_id": metadata["file_id"],
                                "file_name": metadata["file_name"],
                                "original_name": metadata.get("original_name", metadata["file_name"]),
                                "created_at": metadata["created_at"],
                                "file_size": metadata.get("file_size", 0)
                            })
        
        return jsonify({
            "folder_id": folder_id,
            "folder_name": folder_info[0],
            "files": files
        })
        
    except Exception as e:
        return jsonify({"error": f"Failed to get folder files: {str(e)}"}), 500

def update_folder_file_count(user_id, folder_id):
    """Update the file count for a folder"""
    try:
        init_folder_db()
        conn = sqlite3.connect(FOLDER_DB_PATH)
        cursor = conn.cursor()
        
        # Count files in the folder
        folder_metadata_path = os.path.join(DATA_DIR, "users", user_id, "folders", folder_id, "metadata.jsonl")
        file_count = 0
        
        if os.path.exists(folder_metadata_path):
            with open(folder_metadata_path, "r") as f:
                file_count = sum(1 for line in f if line.strip() and "file_name" in json.loads(line))
        
        # Update the file count in the database
        cursor.execute('''
            UPDATE folders 
            SET file_count = ? 
            WHERE folder_id = ? AND user_id = ?
        ''', (file_count, folder_id, user_id))
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        print(f"Error updating folder file count: {str(e)}")

@folder_service.route("/folders/<user_id>/<folder_id>/files", methods=["GET"])
def get_files_in_folder(user_id, folder_id):
    """Get all files in a specific folder"""
    try:
        # Check if folder exists and belongs to user
        conn = sqlite3.connect(FOLDER_DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT folder_name FROM folders WHERE folder_id = ? AND user_id = ?",
            (folder_id, user_id)
        )
        folder = cursor.fetchone()
        
        if not folder:
            conn.close()
            return jsonify({"error": "Folder not found"}), 404
        
        # Get files from the folder's metadata
        folder_metadata_path = get_folder_metadata_path(user_id, folder_id)
        files = []
        
        if os.path.exists(folder_metadata_path):
            with open(folder_metadata_path, 'r') as f:
                for line in f:
                    if line.strip():
                        file_data = json.loads(line)
                        files.append({
                            "file_id": file_data.get("file_id"),
                            "filename": file_data.get("file_name", file_data.get("filename")),
                            "uploaded_at": file_data.get("created_at", file_data.get("uploaded_at")),
                            "file_type": os.path.splitext(file_data.get("original_name", ""))[1] or "Unknown",
                            "file_size": file_data.get("file_size"),
                            "original_name": file_data.get("original_name", "")
                        })
        
        conn.close()
        return jsonify({"files": files})
        
    except Exception as e:
        return jsonify({"error": f"Failed to get files: {str(e)}"}), 500

@folder_service.route("/folders/<user_id>/<folder_id>/context", methods=["GET"])
def get_folder_context(user_id, folder_id):
    """Get context/summary from a specific folder's vector database"""
    try:
        # Check if folder exists and belongs to user
        conn = sqlite3.connect(FOLDER_DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT folder_name, vector_db_name FROM folders WHERE folder_id = ? AND user_id = ?",
            (folder_id, user_id)
        )
        folder = cursor.fetchone()
        
        if not folder:
            conn.close()
            return jsonify({"error": "Folder not found"}), 404
        
        folder_name, vector_db_name = folder
        
        # Get context from vector database
        vector_db_path = get_folder_vector_db_path(user_id, folder_id)
        context = {
            "folder_id": folder_id,
            "folder_name": folder_name,
            "vector_db_name": vector_db_name,
            "context_summary": "This folder contains documents that can be used for context in AI conversations.",
            "file_count": 0,
            "last_updated": None
        }
        
        # Get file count from metadata
        folder_metadata_path = get_folder_metadata_path(user_id, folder_id)
        if os.path.exists(folder_metadata_path):
            file_count = 0
            last_updated = None
            with open(folder_metadata_path, 'r') as f:
                for line in f:
                    if line.strip():
                        file_data = json.loads(line)
                        file_count += 1
                        if not last_updated or file_data.get("uploaded_at", "") > last_updated:
                            last_updated = file_data.get("uploaded_at")
            
            context["file_count"] = file_count
            context["last_updated"] = last_updated
        
        conn.close()
        return jsonify(context)
        
    except Exception as e:
        return jsonify({"error": f"Failed to get folder context: {str(e)}"}), 500

# Initialize the database when the module is imported
init_folder_db()
