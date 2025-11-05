# CampusDoc - Intelligent Educational Platform

A comprehensive full-stack platform that combines Retrieval-Augmented Generation (RAG) capabilities with extensive Google Workspace integrations to create an intelligent educational and administrative management system. What started as a RAG application has evolved into a powerful platform that assists educators and administrators with document management, AI-powered assistance, course management, and automated content generation.

## 🌟 Overview

CampusDoc is not just a document search tool—it's a complete educational ecosystem that leverages AI to streamline administrative tasks, enhance teaching workflows, and provide intelligent document insights. The platform integrates seamlessly with Google Workspace services, enabling educators to manage courses, generate assessments, communicate with students, and search through their document repositories all from a single interface.

## 🚀 Features

### 🤖 AI-Powered Document Intelligence (RAG)

- **Intelligent Document Search**: FAISS-based semantic search to find relevant information across your document collection
- **Document Upload & Processing**: Support for PDF, DOCX, and text files with OCR capabilities for scanned documents
- **Vector Database Management**: Organize documents into folders with separate vector databases for efficient querying
- **Context-Aware Chat**: AI-powered chat interface that uses your documents to provide accurate, context-aware responses
- **Persistent Chat History**: Maintain conversation threads with full history management

### 📚 Educational Management Tools

- **Course Management**: Complete integration with Google Classroom to manage courses, students, and enrollment
- **Student Administration**: View student details, submissions, and coursework across all courses
- **Automated Assessment Generation**:
  - **Question Bank Generator**: AI-powered generation of question banks with customizable difficulty levels and topics
  - **Answer Key Generator**: Automatic creation of answer keys for assessments
  - **Quiz Creation**: Create and publish quizzes directly in Google Classroom
- **Coursework Management**: Create, manage, and track coursework assignments
- **Announcement System**: Create and manage course announcements with attachments

### 📧 Communication & Collaboration

- **Email Integration**: Send emails directly through Gmail API integration
- **Drive File Access**: Download and process files from Google Drive automatically
- **Forms Management**: Access and analyze Google Forms responses
- **File Processing Pipeline**: Automatically process files from Drive and make them searchable

### 🎯 Advanced Capabilities

- **Multi-Folder Context**: Query documents across multiple folders simultaneously
- **Mathematical Content Support**: Full LaTeX rendering for mathematical expressions and formulas
- **Rich Markdown Rendering**: Syntax-highlighted code blocks and formatted text
- **Function Calling**: AI assistant can automatically perform administrative tasks through function calls
- **Sequential Task Execution**: Automatically completes multi-step tasks without user intervention

## 🛠️ Tech Stack

### Backend

- **Framework**: Flask (Python)
- **AI/ML**:
  - Google Gemini AI
  - Sentence Transformers (for embeddings)
  - FAISS (vector similarity search)
  - LangChain (text processing)
- **Database**: SQLite
- **Authentication**: Google OAuth
- **File Processing**: PyPDF2, python-docx, pytesseract (OCR)

### Frontend

- **Framework**: React 19
- **UI Library**: Chakra UI v3
- **Routing**: React Router DOM
- **Markdown**: React Markdown with KaTeX support
- **Build Tool**: Vite

## 🎯 Use Cases

CampusDoc is designed for educators and administrators who need to:

- **Search through extensive document collections** using natural language queries
- **Generate assessments automatically** based on course topics and difficulty levels
- **Manage multiple courses** with automated student and coursework tracking
- **Create and distribute educational content** through Google Classroom
- **Communicate with students** via email and announcements
- **Analyze form responses** and gather feedback efficiently
- **Access and process files** from Google Drive automatically
- **Maintain organized document repositories** with folder-based vector databases

## 📋 Prerequisites

- Python 3.8+
- Node.js 16+
- npm or yarn
- Google Cloud Project with enabled APIs:
  - Google Generative AI API
  - Google Classroom API
  - Google Drive API
  - Gmail API
  - Google Forms API
- Google OAuth 2.0 credentials
- Poppler (for PDF image conversion on some systems)

## 🔧 Installation

### Backend Setup

1. Navigate to the server directory:

   ```bash
   cd server
   ```

2. Create a virtual environment:

   ```bash
   python -m venv venv
   ```

3. Activate the virtual environment:

   ```bash
   # On macOS/Linux
   source venv/bin/activate

   # On Windows
   venv\Scripts\activate
   ```

4. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

5. Create a `.env` file in the `server` directory. You can copy from `.env.example`:

   ```bash
   cp .env.example .env
   ```

   Then edit `.env` and set the following required variables:

   ```env
   FLASK_SECRET_KEY=your-secret-key-here-change-in-production
   GOOGLE_API_KEY=your_google_api_key
   GEMINI_MODEL_NAME=gemini-2.5-pro
   EMBED_MODEL_NAME=all-MiniLM-L6-v2
   DATA_DIR=./data
   INDEX_PATH=./faiss_index.bin
   METADATA_PATH=./metadata.json
   OAUTH_REDIRECT_URI=http://localhost:5001/api/auth/oauth2callback
   ```

6. Set up Google OAuth credentials:
   - Download OAuth 2.0 credentials from Google Cloud Console
   - Save as `creds.json` in the `server` directory
   - Ensure OAuth consent screen is configured with required scopes:
     - Google Classroom API (read/write)
     - Google Drive API (read)
     - Gmail API (send)
     - Google Forms API (read)

### Frontend Setup

1. Navigate to the client directory:

   ```bash
   cd client
   ```

2. Install dependencies:

   ```bash
   npm install
   ```

3. Create a `.env` file in the `client` directory (if needed):
   ```env
   VITE_API_URL=http://localhost:5000
   ```

## 🚦 Running the Application

### Start the Backend Server

From the `server` directory:

```bash
python app.py
```

The API will be available at `http://localhost:5001` (or the port specified in `FLASK_PORT`)

### Start the Frontend Development Server

From the `client` directory:

```bash
npm run dev
```

The application will be available at `http://localhost:5173` (or the port Vite assigns)

## 📁 Project Structure

```
Rag_Project/
├── server/                 # Flask backend
│   ├── app.py             # Main Flask application
│   ├── routes/            # API route handlers
│   │   ├── ai_service.py
│   │   ├── authorization.py
│   │   ├── classroom_service.py
│   │   ├── drive_service.py
│   │   ├── email_service.py
│   │   ├── file_service.py
│   │   ├── folder_service.py
│   │   └── forms_service.py
│   ├── db_utils/          # Database utilities
│   └── requirements.txt
├── client/                # React frontend
│   ├── src/
│   │   ├── components/    # React components
│   │   ├── App.jsx        # Main app component
│   │   └── main.jsx       # Entry point
│   └── package.json
└── requirements.txt       # Root requirements
```

## 🔐 Environment Variables

### Backend (.env)

**Required Variables:**
- `FLASK_SECRET_KEY`: Secret key for Flask sessions (required, no default)
- `GOOGLE_API_KEY`: Your Google API key for Gemini AI
- `GEMINI_MODEL_NAME`: Gemini model name (e.g., `gemini-2.5-pro`)
- `EMBED_MODEL_NAME`: Embedding model name (e.g., `all-MiniLM-L6-v2`)
- `DATA_DIR`: Directory for storing user data
- `INDEX_PATH`: Path to FAISS index file
- `METADATA_PATH`: Path to metadata JSON file

**Optional Variables:**
- `FLASK_PORT`: Port for Flask server (default: `5001`)
- `FLASK_DEBUG`: Enable debug mode (default: `False`)
- `OAUTH_REDIRECT_URI`: OAuth callback URL (default: `http://localhost:5001/api/auth/oauth2callback`)
- `GOOGLE_OAUTH_CREDENTIALS_FILE`: Path to OAuth credentials file (default: `credentials.json`)
- `GOOGLE_OAUTH_CREDS_FILE`: Path to store OAuth tokens (default: `creds.json`)

## 📝 API Endpoints

### Authentication

- `POST /auth/google` - Initiate Google OAuth flow
- `GET /auth/callback` - OAuth callback handler
- `GET /auth/user` - Get current authenticated user information

### Files & Documents

- `POST /files/upload` - Upload a document (PDF, DOCX, TXT)
- `GET /files` - List user's files
- `DELETE /files/<file_id>` - Delete a file
- `GET /files/<file_id>` - Get file metadata

### Folders & Organization

- `POST /folders` - Create a folder
- `GET /folders` - List user's folders
- `GET /folders/<folder_id>` - Get folder details
- `DELETE /folders/<folder_id>` - Delete a folder

### Chat & AI Assistant

- `POST /chat/query` - Send a chat message (supports function calling)
- `GET /chat/threads` - Get all chat threads
- `POST /chat/threads` - Create a new chat thread
- `DELETE /chats/<chat_id>` - Delete a chat thread

### Google Classroom Integration

- `GET /classroom/courses` - List all courses
- `GET /classroom/courses/<course_id>/students` - List course students
- `GET /classroom/courses/<course_id>/coursework` - List coursework
- `POST /classroom/courses/<course_id>/announcements` - Create announcement
- `POST /classroom/courses/<course_id>/coursework` - Create coursework

### Google Drive & Forms

- `POST /drive/download` - Download file from Drive
- `GET /forms` - List all forms
- `GET /forms/<form_id>/responses` - Get form responses

### Email

- `POST /email/send` - Send email via Gmail API

## 🧠 How It Works

### AI Assistant with Function Calling

The platform's AI assistant is powered by Google Gemini AI and features advanced function calling capabilities. When you ask the assistant a question or request an action, it can:

- **Automatically perform administrative tasks** without requiring you to provide IDs or parameters
- **Sequentially execute multi-step workflows** (e.g., list courses → get students → retrieve submissions)
- **Generate content dynamically** (question banks, answer keys, quizzes) based on course topics
- **Search through your documents** using RAG to provide context-aware responses
- **Integrate with Google Workspace** to manage courses, send emails, and access files

The assistant understands natural language requests and automatically determines which functions to call and in what order, making it feel like a true AI assistant rather than just a search tool.

### RAG Architecture

- Documents are chunked using LangChain's RecursiveCharacterTextSplitter
- Chunks are embedded using Sentence Transformers
- FAISS indexes store embeddings for fast similarity search
- Each folder maintains its own vector database for isolation
- Context from multiple folders can be combined for comprehensive queries

## 🧪 Development

### Backend Development

- The Flask app runs in development mode by default
- Debug mode is enabled for better error messages
- CORS is configured to allow frontend connections
- Function calling is integrated with Google Gemini AI

### Frontend Development

- Hot module replacement enabled
- ESLint configured for code quality
- React Router for client-side routing
- Chakra UI for modern, responsive components

## 📦 Building for Production

### Frontend Build

```bash
cd client
npm run build
```

The production build will be in `client/dist/`

### Backend Deployment

- Ensure all environment variables are set
- Use a production WSGI server (e.g., Gunicorn)
- Configure proper CORS settings for production domain

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📧 Contact

For questions or support, please contact: [spbalaji659@gmail.com]

## 🔗 Repository

[Repository URL: https://github.com/Balaji-S-P/CampusDoc]

## 🙏 Acknowledgments

- Google Generative AI for Gemini models
- Sentence Transformers for embedding models
- FAISS for efficient vector search
- Chakra UI for the component library
