import os
import faiss
import json
from google import genai    

from dotenv import load_dotenv
from flask import Flask, request, jsonify 
from flask_cors import CORS
from sentence_transformers import SentenceTransformer
from langchain.text_splitter import RecursiveCharacterTextSplitter
import uuid
from datetime import datetime
from routes import create_app
from db_utils.db_helper import user_exists
from db_utils.db_helper import save_tokens
from db_utils.db_helper import get_tokens
from db_utils.db_helper import init_db
from routes.email_service import handle_part



# Chat storage directory
CHAT_STORAGE_DIR = "chat_histories"
if not os.path.exists(CHAT_STORAGE_DIR):
    os.makedirs(CHAT_STORAGE_DIR)

class DocSearch:
    def __init__(self):

        self.DATA_DIR = os.getenv("DATA_DIR")
        self.INDEX_PATH = os.getenv("INDEX_PATH")
        self.METADATA_PATH = os.getenv("METADATA_PATH")
        self.EMBED_MODEL_NAME = os.getenv("EMBED_MODEL_NAME")
        self.EMBED_DIM = 384
        self.CHUNK_SIZE = 1500
        self.CHUNK_OVERLAP = 300
        self.GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME")
        self.embedder = SentenceTransformer(self.EMBED_MODEL_NAME)
        self.client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
        # Use langchain's RecursiveCharacterTextSplitter for chunking
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.CHUNK_SIZE,
            chunk_overlap=self.CHUNK_OVERLAP
        )
        if os.path.exists(self.INDEX_PATH) and os.path.exists(self.METADATA_PATH):
            self.index = faiss.read_index(self.INDEX_PATH)
            with open(self.METADATA_PATH, "r") as f:
                self.metadata = json.load(f)
            print(f"Loaded existing metadata from {self.METADATA_PATH}")
            print(f"Loaded existing FAISS index from {self.INDEX_PATH}")
        else:
            print(f"No existing FAISS index found at {self.INDEX_PATH}, building new one")
            self.index = faiss.IndexFlatL2(self.EMBED_DIM)
            self.metadata = []
            # Persist the newly created empty index and metadata for future use
            faiss.write_index(self.index, self.INDEX_PATH)
            with open(self.METADATA_PATH, "w") as f:
                json.dump(self.metadata, f)
            print(f"Initialized and saved new FAISS index to {self.INDEX_PATH}")
            print(f"Initialized and saved new metadata to {self.METADATA_PATH}")
        
    def get_chunks(self, doc):
        chunks = self.text_splitter.split_text(doc)
        return chunks
    
    def embed_chunks(self, chunks):
        embeddings = self.embedder.encode(chunks)
        return embeddings

    def ingest_docs(self, docs):
        for doc in docs:
            chunks = self.get_chunks(doc)
            embeddings = self.embed_chunks(chunks)
            self.add_to_index(embeddings,doc,chunks)
    
    def add_to_index(self, embeddings, doc, chunks):
        self.index.add(embeddings)
        # Store metadata for each chunk
        doc_id=str(uuid.uuid4())
        for i, embedding in enumerate(embeddings):
            self.metadata.append({
                "doc_id": doc_id,
                "chunk_id": doc_id + "_" + str(i),
                "chunk_text": chunks[i]
            })
        # Save updated metadata
        with open(self.METADATA_PATH, "w") as f:
            json.dump(self.metadata, f)
        # Save updated index
        faiss.write_index(self.index, self.INDEX_PATH)
    
    def search(self, query, k=5):
        query_embedding = self.embedder.encode([query])
        distances, indices = self.index.search(query_embedding, k)
        return distances, indices
    
    def get_context(self, query, k=5, selected_folders=None, user_id=None):
        print(f"DEBUG: get_context called with query='{query}', selected_folders={selected_folders}, user_id={user_id}")
        if selected_folders and user_id:
            # Ensure user_id is a string
            user_id = str(user_id)
            # Search through selected folders
            context = []
            for folder_id in selected_folders:
                print(f"DEBUG: Getting context from folder {folder_id}")
                folder_context = self.get_folder_context(query, str(folder_id), user_id, k)
                print(f"DEBUG: Folder {folder_id} returned {len(folder_context)} context items")
                context.extend(folder_context)
            print(f"DEBUG: Total context from selected folders: {len(context)} items")
            return context[:k]  # Limit to k results
        else:
            # Original behavior - search through general index
            distances, indices = self.search(query, k)
            context = []
            for i in range(len(indices[0])):  # indices is a 2D array
                if indices[0][i] < len(self.metadata):  # Check bounds
                    context.append(self.metadata[indices[0][i]]['chunk_text'])
            return context
    
    def get_folder_context(self, query, folder_id, user_id, k=5):
        """Get context from a specific folder's vector database"""
        try:
            from sentence_transformers import SentenceTransformer
            import faiss
            import json
            import os
            
            # Validate inputs
            print(f"DEBUG: get_folder_context inputs - query: {type(query)}='{query}', folder_id: {type(folder_id)}='{folder_id}', user_id: {type(user_id)}='{user_id}'")
            if not query or not folder_id or not user_id:
                print("Invalid inputs for get_folder_context")
                return []
            
            # Ensure user_id is a string
            user_id = str(user_id)
            folder_id = str(folder_id)
            
            # Get folder vector database path
            vector_db_path = os.path.join(self.DATA_DIR, "vector_dbs", f"{user_id}_{folder_id}.bin")
            metadata_path = os.path.join(self.DATA_DIR, "users", user_id, "folders", folder_id, "metadata.jsonl")
            
            if not os.path.exists(vector_db_path):
                print(f"Vector database not found: {vector_db_path}")
                return []
                
            if not os.path.exists(metadata_path):
                print(f"Metadata file not found: {metadata_path}")
                return []
            
            print(f"DEBUG: Found vector DB: {vector_db_path}")
            print(f"DEBUG: Found metadata: {metadata_path}")
            
            # Load folder's vector database
            folder_index = faiss.read_index(vector_db_path)
            
            # Load folder's metadata
            folder_metadata = []
            with open(metadata_path, 'r') as f:
                for line in f:
                    if line.strip():
                        try:
                            folder_metadata.append(json.loads(line))
                        except json.JSONDecodeError as e:
                            print(f"Error parsing metadata line: {e}")
                            continue
            
            if not folder_metadata:
                print("No valid metadata found")
                return []
            
            print(f"DEBUG: Loaded {len(folder_metadata)} metadata entries")
            
            # Search in folder's vector database
            query_embedding = self.embedder.encode([query])
            distances, indices = folder_index.search(query_embedding, k)
            
            print(f"DEBUG: Search returned {len(indices[0])} results")
            print(f"DEBUG: Indices: {indices[0]}")
            print(f"DEBUG: Distances: {distances[0]}")
            
            context = []
            for i in range(len(indices[0])):
                if indices[0][i] < len(folder_metadata):
                    chunk_text = folder_metadata[indices[0][i]].get('chunk_text', '')
                    print(f"DEBUG: Result {i}: index={indices[0][i]}, chunk_text length={len(chunk_text)}")
                    if chunk_text:
                        context.append(chunk_text)
            
            print(f"DEBUG: Final context length: {len(context)}")
            return context
            
        except Exception as e:
            print(f"Error getting folder context for folder {folder_id}: {str(e)}")
            return []
    
    def format_prompt(self, query, context, user_id=None):
        """Format the prompt for Gemini with proper context"""
        print(f"DEBUG: format_prompt called with context={len(context) if context else 0} items")
        if context and len(context) > 0:
            formatted_context = "\n\n".join([f"Context {i+1}: {text}" for i, text in enumerate(context)])
            print(f"DEBUG: Formatted context length: {len(formatted_context)} characters")
        else:
            formatted_context = ""
            print("DEBUG: No context provided to format_prompt")
        
        # Add function calling information
        function_info = ""
        if user_id:
            function_info = f"""

AVAILABLE FUNCTIONS:
You have access to the following functions to help answer questions:

1. **list_courses()** - List all classroom courses the user is enrolled in
2. **list_course_students(course_id)** - List all students in a specific course
3. **get_student(course_id, student_id)** - Get details about a specific student
4. **list_student_submissions(course_id, student_id)** - List all submissions for a student
5. **get_coursework(course_id, coursework_id, student_id)** - Get details about specific coursework
6. **get_coursework_materials(course_id, coursework_id)** - Get materials for a specific coursework
7. **list_courseworks(course_id)** - List all coursework for a course
8. **send_email(to, subject, message)** - Send an email to someone
9. **download_file_from_drive_and_upload_to_gemini(file_id)** - Download a file from Google Drive and upload it to Gemini
10. **create_quiz(quiz_name, quiz_description, quiz_questions)** - Create a quiz
11. **create_announcement(course_id, announcement_body, materials)** - Create an announcement for a course
12. **list_forms()** - List all forms
13. **get_form(form_id)** - Get details about a specific form
14. **list_form_responses(form_id)** - List all responses for a specific form
15. **get_form_response(form_id, response_id)** - Get details about a specific response\
16. **question_bank_generator(course_code, course_name, module_number, sections, include_images, dep)** - Generate a question bank for a course and upload it to Google Drive. IMPORTANT: You must generate the actual questions yourself based on the course topic. Each section must have part_label, marks, and questions array with actual question text that you create. For images, only include image_ref if you have a real, working image URL - do not use example.com or placeholder URLs.
17. **answer_key_generator(course_code, course_name, module_number, sections, include_images, dep)** - Generate a answer key for a course and upload it to Google Drive. IMPORTANT: You must generate the actual answers yourself based on the course topic. Each section must have part_label, marks, and answers array with actual answer text that you create. For images, only include image_ref if you have a real, working image URL - do not use example.com or placeholder URLs.
18. **create_coursework(course_id, coursework_body)** - Create a coursework for a course
When the user asks about their courses, enrollment, or classroom-related information, use the appropriate function to get the most current data.

CRITICAL: You MUST make sequential function calls automatically. Do NOT ask the user for course IDs or other parameters.

MOST IMPORTANT: Always complete the user's full request. If the user asks for something that requires multiple steps, complete ALL steps before responding. Do NOT stop midway with phrases like "I will now proceed to..." - instead, immediately continue with the next required action. The user expects a complete solution, not a partial one.

RESPONSE GENERATION: After completing all tasks, ALWAYS provide a clear, detailed summary of what was accomplished. Include specific details like file names, course names, due dates, and any other relevant information. Do NOT end with generic messages - give the user concrete information about what was created or processed.

CRITICAL: Always focus on the CURRENT user request. Ignore previous conversation history when determining what to create. If the user asks for "red black tree" question bank, create exactly that - do NOT create something else based on previous requests. Each request should be treated independently.

QUESTION BANK GENERATION: When using the question_bank_generator function, you MUST generate the actual questions yourself. Do NOT ask the user to provide questions. Create relevant, educational questions based on the course topic and difficulty level specified. For images, only include image_ref if you have access to real, working image URLs. Do NOT generate fake URLs like example.com.

IMPORTANT: When generating question banks, use EXACTLY the topic specified in the user's current request. If the user asks for "red black tree" questions, create questions about red black trees. If they ask for "cloud services" questions, create questions about cloud services. Do NOT mix up topics from previous conversation history.

COURSEWORK CREATION: When using the create_coursework function, you MUST create the coursework yourself. Do NOT ask the user to provide coursework details. Create the coursework based on the course topic and difficulty level specified.

CRITICAL: When creating coursework, ALWAYS use a future due date (at least 1 week from today). Use the current date and add 7-14 days for the due date. The dueDate must be in the future or the API will reject the request.

For example:
- If asked about "students in math courses" or "students in courses", you MUST:
  1. First call list_courses() to get all courses
  2. Then call list_course_students(course_id) for each course found
  3. Filter and present the results based on the user's request

- If asked about submissions, you MUST:
  1. First call list_courses() to get courses
  2. Then call list_course_students(course_id) to get students  
  3. Then call list_student_submissions(course_id, student_id) for each student

NEVER ask the user for course IDs, student IDs, or other parameters that you can obtain through function calls. Always make the necessary function calls automatically.

After calling functions, always provide a clear, helpful response based on the function results. If the function returns an empty result, explain what that means to the user.

MATHEMATICAL CONTENT HANDLING:
- When presenting mathematical expressions, calculations, or formulas, use proper LaTeX formatting
- For matrices, use this exact format (raw text, no code blocks):
  $$
  \\begin{{pmatrix}}
  a & b \\\\
  c & d
  \\end{{pmatrix}}
  $$
- For inline math, use: $expression$
- For block math, use: $$expression$$ (with newlines)
- Always include newlines after opening $$ and before closing $$
- Ensure mathematical notation is clear and properly formatted
- Always escape curly braces in LaTeX: use {{ and }}
- CRITICAL: NEVER wrap LaTeX expressions in code blocks (```). LaTeX should be raw text, not code. 

USER ID: {user_id}
"""
        
        prompt = f"""You are an expert educational consultant specializing in Sri Krishna College of Engineering and Technology (SKCET). Your role is to provide comprehensive, accurate, and engaging responses about SKCET

RESPONSE GUIDELINES:
1. **Comprehensive Coverage**: Address all aspects of the question thoroughly
2. **Specific Details**: Include exact numbers, dates, statistics, and concrete facts
3. **Structured Format**: Use clear headings, bullet points, and logical organization
4. **Context & Background**: Provide relevant context to enhance understanding
5. **Professional Tone**: Be informative yet conversational and approachable
6. **Visual Hierarchy**: Use markdown formatting for better readability
7. **Mathematical Expressions**: Use LaTeX formatting for mathematical content:
   - Inline math: $x^2 + y^2 = z^2$
   - Block math: Use proper formatting with newlines:
     $$
     \\begin{{pmatrix}}
     a & b \\\\
     c & d
     \\end{{pmatrix}}
     $$
   - Always include newlines after opening $$ and before closing $$
   - Use proper LaTeX syntax for matrices, equations, and mathematical notation
   - Always escape curly braces: use {{ and }}
   - CRITICAL: NEVER wrap LaTeX expressions in code blocks (```). LaTeX should be raw text, not code. 

SPECIALIZED SECTIONS:
- **Programs**: Include duration, fees, intake, eligibility, specializations
- **Facilities**: Describe infrastructure, equipment, capacity, features
- **Placements**: Provide statistics, company names, salary ranges, trends
- **Admissions**: Include requirements, process, deadlines, criteria
- **Campus Life**: Mention events, clubs, activities, culture
- **Achievements**: Highlight awards, rankings, recognitions, milestones

CONTEXT INFORMATION:
{formatted_context}{function_info}

USER QUESTION: {query}

IMPORTANT: If the context contains markdown formatting (like headings, code blocks, lists, etc.), preserve that formatting in your response. Use the same markdown structure and formatting that appears in the context.

EXPERT RESPONSE:"""
        return prompt
    
    def enhance_query(self, query):
        """Enhance query with related terms for better context matching"""
        enhanced_terms = {
            "placement": ["job", "career", "recruitment", "company", "salary", "package"],
            "admission": ["apply", "eligibility", "requirement", "process", "criterion"],
            "program": ["course", "degree", "curriculum", "subject", "specialization"],
            "facility": ["infrastructure", "lab", "library", "hostel", "campus"],
            "event": ["conference", "workshop", "festival", "competition", "celebration"]
        }
        
        query_lower = query.lower()
        enhanced_query = query
        
        for key, terms in enhanced_terms.items():
            if any(term in query_lower for term in [key] + terms):
                enhanced_query += " " + " ".join(terms)
                break
                
        return enhanced_query

    def get_response(self, query, k=12,user_id=None,selected_folders=None,chat_id=None):
        # Enhance query for better context matching
        enhanced_query = self.enhance_query(query)
        history=self.get_chat(chat_id)
        contents=[]
        for message in history["messages"]:
            if message["role"] == "user":
                contents.append(genai.types.Content(
                    role="user",
                    parts=[genai.types.Part(text=message["content"])]
                ))
            elif message["role"] == "assistant":
                contents.append(genai.types.Content(
                    role="model",
                    parts=[genai.types.Part(text=message["content"])]
                ))
        # Only get context if selected folders are provided and user_id exists
        context = None
        print(f"DEBUG: get_response called with selected_folders={selected_folders}, user_id={user_id}")
        if selected_folders and user_id:
            # Ensure selected_folders is a list
            if isinstance(selected_folders, str):
                selected_folders = [selected_folders]
            if len(selected_folders) > 0:
                try:
                    context = self.get_context(enhanced_query, k, selected_folders, user_id)
                    if not context or len(context) == 0:
                        context = None
                except Exception as e:
                    print(f"Error getting context from selected folders: {str(e)}")
                    context = None
       
        
        # Format the prompt properly
        prompt = self.format_prompt(query, context, user_id)
        contents.append(
    genai.types.Content(
        role="user", parts=[genai.types.Part(text=prompt)]
    )
        )
        try:
            # Use Gemini to generate response
            final_response = ""
            max_iterations = 10  # Prevent infinite loops
            iteration = 0
            
            while iteration < max_iterations:
                iteration += 1
                print(f"Iteration {iteration}")
                
                response = self.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=contents,
                    config=config
                )
                
                if not response.candidates:
                    print("No candidates in response")
                    break
                
                function_called = False
                text_response = ""
                
                for candidate in response.candidates:
                    if candidate.content and candidate.content.parts:
                        for part in candidate.content.parts:
                            if part.function_call:
                                print(f"Function call detected: {part.function_call.name}")
                                print(f"Function args: {part.function_call.args}")
                                function_called = True
                                
                                try:
                                    function_response = handle_part(part, user_id)
                                    print(f"Function response: {function_response}")
                                    
                                    if function_response:
                                        # Add function response to conversation
                                        functions_response_part = genai.types.Part.from_function_response(
                                            name=part.function_call.name,
                                            response={"result": function_response}
                                        )
                                        contents.append(genai.types.Content(role="user", parts=[functions_response_part]))
                                except Exception as e:
                                    print(f"Error handling function call: {e}")
                                    # Continue with the conversation even if function call fails
                                    continue
                                    
                            elif part.text:
                                text_response += part.text + "\n"
                                print(f"Text response: {text_response}")
                    
                    # Check if we should stop the loop
                    if hasattr(candidate, 'finish_reason'):
                        print(f"Finish reason: {candidate.finish_reason}")
                        if candidate.finish_reason == "stop" and text_response:
                            print("Stopping loop - got text response with stop reason")
                            final_response = text_response
                            break
                        elif candidate.finish_reason == "stop" and not function_called:
                            print("Stopping loop - stop reason but no function called and no text")
                            break
                        elif candidate.finish_reason == "malformed_function_call":
                            print("Malformed function call detected - stopping loop")
                            if text_response:
                                final_response = text_response
                            break
                
                # If we got a text response and no function was called, we're done
                if text_response and not function_called:
                    final_response = text_response
                    break
                
                # If no function was called and no text response, we're done
                if not function_called and not text_response:
                    print("No function called and no text response - stopping")
                    break
                
                # If a function was called, continue the loop to allow for sequential calls
                if function_called:
                    print("Function was called, continuing loop for potential sequential calls...")
                    # Add a prompt to encourage response generation after function calls
                    if iteration >= 2:  # After at least one function call
                        contents.append(genai.types.Content(
                            role="user", 
                            parts=[genai.types.Part(text="Continue working on the user's request. If you need to call more functions to complete the task, do so now. Only provide a final response when you have fully completed all required steps.")]
                        ))
                    continue
                            
                # print(f"Final response: {final_response}")
                # Validate and enhance response
            # Debug: Write response info to file
            debug_info = {
                "final_response": final_response,
                "contents_count": len(contents),
                "contents_summary": []
            }
            for i, content in enumerate(contents):
                if hasattr(content, 'role') and hasattr(content, 'parts'):
                    parts_summary = []
                    for part in content.parts:
                        if hasattr(part, 'text') and part.text:
                            parts_summary.append({"type": "text", "preview": part.text[:100] + "..." if len(part.text) > 100 else part.text})
                        elif hasattr(part, 'function_call') and part.function_call:
                            parts_summary.append({"type": "function_call", "name": part.function_call.name})
                        elif hasattr(part, 'function_response') and part.function_response:
                            parts_summary.append({"type": "function_response", "name": getattr(part.function_response, 'name', 'unknown')})
                    debug_info["contents_summary"].append({
                        "index": i,
                        "role": content.role,
                        "parts": parts_summary
                    })
            
            with open("debug.json", "w") as f:
                json.dump(debug_info, f, indent=2)
            if final_response:
                response_text = final_response.strip()
            else:
                # Check if any functions were called in the conversation
                functions_called = any("function_response" in str(content) for content in contents)
                if functions_called:
                    # If functions were called successfully, provide a better response
                    response_text = "I have successfully completed your request. All the requested tasks have been processed and the results are ready for your use."
                else:
                    response_text = "I checked your classroom courses, but it appears you are not currently enrolled in any courses. This could mean either you haven't been added to any courses yet, or there might be an issue with the course enrollment data."
            return response_text
            
        except Exception as e:
            print(e)
            return "An error occurred while generating the response."

    def get_response_with_files(self, query, k=12, user_id=None, uploaded_files=None,selected_folders=None,chat_id=None):
        """Generate response with uploaded files using Files API"""
        # Enhance query for better context matching
        enhanced_query = self.enhance_query(query)
        history=self.get_chat(chat_id)
        # Only get context if selected folders are provided and user_id exists
        contents=[]
        for message in history["messages"]:
            if message["role"] == "user":
                contents.append(genai.types.Content(
                    role="user",
                    parts=[genai.types.Part(text=message["content"])]
                ))
            elif message["role"] == "assistant":
                contents.append(genai.types.Content(
                    role="model",
                    parts=[genai.types.Part(text=message["content"])]
                ))
        
        context = None
        if selected_folders and user_id:
            # Ensure selected_folders is a list
            if isinstance(selected_folders, str):
                selected_folders = [selected_folders]
            if len(selected_folders) > 0:
                try:
                    context = self.get_context(enhanced_query, k, selected_folders, user_id)
                    if not context or len(context) == 0:
                        context = None
                except Exception as e:
                    print(f"Error getting context from selected folders: {str(e)}")
                    context = None
        
        
        # Format the prompt properly
        prompt=self.format_prompt(query, context, user_id)
        
        # Build contents with files and text
        
        # Upload files to Gemini Files API and add them to content
        if uploaded_files:
            from routes.ai_service import upload_to_gemini
            
            for file in uploaded_files:
                try:
                    # Upload file to Gemini Files API
                    upload_result = upload_to_gemini(file)

                    if upload_result["success"]:
                        # Add the file as a separate content item
                        contents.append(upload_result["file"])
                        display_name = upload_result.get('display_name', file.filename or 'Unknown')
                        print(f"Successfully uploaded file: {display_name}")
                    else:
                        print(f"Failed to upload file {file.filename}: {upload_result['error']}")
                        
                except Exception as e:
                    print(f"Error processing file {file.filename}: {str(e)}")
                    continue
        
        # Add text prompt as a separate content item
        contents.append(genai.types.Content(
            role="user", 
            parts=[genai.types.Part(text=prompt)]
        ))

        try:
            # Use Gemini to generate response with sequential function calls
            final_response = ""
            max_iterations = 10  # Prevent infinite loops
            iteration = 0
            
            while iteration < max_iterations:
                iteration += 1
                print(f"Iteration {iteration}")
                
                response = self.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=contents,
                    config=config
                )
                
                if not response.candidates:
                    print("No candidates in response")
                    break
                
                function_called = False
                text_response = ""
                
                for candidate in response.candidates:
                    if candidate.content and candidate.content.parts:
                        for part in candidate.content.parts:
                            if part.function_call:
                                print(f"Function call detected: {part.function_call.name}")
                                print(f"Function args: {part.function_call.args}")
                                function_called = True
                                
                                try:
                                    function_response = handle_part(part, user_id)
                                    print(f"Function response: {function_response}")
                                    
                                    if function_response:
                                        # Add function response to conversation
                                        functions_response_part = genai.types.Part.from_function_response(
                                            name=part.function_call.name,
                                            response={"result": function_response}
                                        )
                                        contents.append(genai.types.Content(role="user", parts=[functions_response_part]))
                                except Exception as e:
                                    print(f"Error handling function call: {e}")
                                    # Continue with the conversation even if function call fails
                                    continue
                                    
                            elif part.text:
                                text_response += part.text + "\n"
                                print(f"Text response: {text_response}")
                    
                    # Check if we should stop the loop
                    if hasattr(candidate, 'finish_reason'):
                        print(f"Finish reason: {candidate.finish_reason}")
                        if candidate.finish_reason == "stop" and text_response:
                            print("Stopping loop - got text response with stop reason")
                            final_response = text_response
                            break
                        elif candidate.finish_reason == "stop" and not function_called:
                            print("Stopping loop - stop reason but no function called and no text")
                            break
                        elif candidate.finish_reason == "malformed_function_call":
                            print("Malformed function call detected - stopping loop")
                            if text_response:
                                final_response = text_response
                            break
                
                # If we got a text response and no function was called, we're done
                if text_response and not function_called:
                    final_response = text_response
                    break
                
                # If no function was called and no text response, we're done
                if not function_called and not text_response:
                    print("No function called and no text response - stopping")
                    break
                
                # If a function was called, continue the loop to allow for sequential calls
                if function_called:
                    print("Function was called, continuing loop for potential sequential calls...")
                    # Add a prompt to encourage response generation after function calls
                    if iteration >= 2:  # After at least one function call
                        contents.append(genai.types.Content(
                            role="user", 
                            parts=[genai.types.Part(text="Continue working on the user's request. If you need to call more functions to complete the task, do so now. Only provide a final response when you have fully completed all required steps.")]
                        ))
                    continue
                            
            # Debug: Write response info to file
            debug_info = {
                "final_response": final_response,
                "contents_count": len(contents),
                "contents_summary": []
            }
            for i, content in enumerate(contents):
                if hasattr(content, 'role') and hasattr(content, 'parts'):
                    parts_summary = []
                    for part in content.parts:
                        if hasattr(part, 'text') and part.text:
                            parts_summary.append({"type": "text", "preview": part.text[:100] + "..." if len(part.text) > 100 else part.text})
                        elif hasattr(part, 'function_call') and part.function_call:
                            parts_summary.append({"type": "function_call", "name": part.function_call.name})
                        elif hasattr(part, 'function_response') and part.function_response:
                            parts_summary.append({"type": "function_response", "name": getattr(part.function_response, 'name', 'unknown')})
                    debug_info["contents_summary"].append({
                        "index": i,
                        "role": content.role,
                        "parts": parts_summary
                    })
            
            with open("debug.json", "w") as f:
                json.dump(debug_info, f, indent=2)
            
            # Validate and enhance response
            if final_response:
                response_text = final_response.strip()
            else:
                # Check if any functions were called in the conversation
                functions_called = any("function_response" in str(content) for content in contents)
                if functions_called:
                    response_text = "I have successfully completed your request. All the requested tasks have been processed and the results are ready for your use."
                else:
                    response_text = "I checked your classroom courses, but it appears you are not currently enrolled in any courses. This could mean either you haven't been added to any courses yet, or there might be an issue with the course enrollment data."
            return response_text
            
        except Exception as e:
            print(e)
            return "An error occurred while generating the response."

    def generate_fallback_response(self, query, context):
        """Generate a fallback response when AI fails"""
        if not context:
            return "I apologize, but I couldn't find specific information about that topic. Please try rephrasing your question or ask about SKCET's programs, facilities, placements, or admissions."
        
        # Extract key information from context
        key_info = []
        for ctx in context[:3]:  # Use top 3 contexts
            if "placement" in query.lower() and any(word in ctx.lower() for word in ["placement", "salary", "company"]):
                key_info.append(ctx)
            elif "program" in query.lower() and any(word in ctx.lower() for word in ["program", "course", "degree"]):
                key_info.append(ctx)
            elif "facility" in query.lower() and any(word in ctx.lower() for word in ["facility", "infrastructure", "lab"]):
                key_info.append(ctx)
        
        if key_info:
            return f"Based on the available information about SKCET:\n\n" + "\n\n".join(key_info[:2])
        else:
            return "I found some information about SKCET, but I'm having trouble generating a complete response. Here's what I found:\n\n" + context[0] if context else "Please try asking about SKCET's specific programs, facilities, or placements."
    
    def extract_text_from_file(self, file_path):
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()

    def extract_text_from_json(self, file_path):
        with open(file_path, 'r', encoding='utf-8') as file:
            data=json.load(file)
        return json.dumps(data)
    
    def ingest_file(self, file_path):
        text=self.extract_text_from_file(file_path)
        self.ingest_docs([text])
        return jsonify({"message": "File ingested successfully", "count": 1})


    def reset_index(self):
        self.index.reset()
        self.metadata = []
        faiss.write_index(self.index, self.INDEX_PATH)
        with open(self.METADATA_PATH, "w") as f:
            json.dump(self.metadata, f)
        return jsonify({"message": "Index reset successfully"})

    def add_to_chat(self, chat_id, message):
        if chat_id is None:
            chat_id = str(uuid.uuid4())
        
        if not message:
            return None
            
        filepath = os.path.join(CHAT_STORAGE_DIR, f"{chat_id}.json")
        
        # Create chat file if it doesn't exist
        if not os.path.exists(filepath):
            chat_data = {
                "id": chat_id,
                "title": "New Chat",
                "messages": [],
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(chat_data, f, indent=2)
        
        # Read existing chat data
        with open(filepath, 'r', encoding='utf-8') as f:
            chat_data = json.load(f)
        
        # Add message
        chat_data["messages"].append(message)
        chat_data["updated_at"] = datetime.now().isoformat()
        
        # Update title if it's the first user message
        if message.get("role") == "user" and chat_data["title"] == "New Chat":
            chat_data["title"] = message["content"][:50] + "..." if len(message["content"]) > 50 else message["content"]
        
        # Save updated chat data
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(chat_data, f, indent=2)
        
        return chat_id
        
    def get_chats(self):
        try:
            chats = []
            if not os.path.exists(CHAT_STORAGE_DIR):
                return chats
                
            for filename in os.listdir(CHAT_STORAGE_DIR):
                if filename.endswith('.json'):
                    chat_id = filename[:-5]
                    filepath = os.path.join(CHAT_STORAGE_DIR, filename)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            chat_data = json.load(f)
                            chats.append({
                                "id": chat_id,
                                "title": chat_data.get("title", "New Chat"),
                                "created_at": chat_data.get("created_at", ""),
                                "updated_at": chat_data.get("updated_at", "")
                            })
                    except (json.JSONDecodeError, IOError) as e:
                        print(f"Error reading chat file {filename}: {e}")
                        continue
            
            # Sort by updated_at descending
            chats.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
            return chats
        except Exception as e:
            print(f"Error getting chats: {e}")
            return []
    
    def get_chat(self, chat_id):
        filepath = os.path.join(CHAT_STORAGE_DIR, f"{chat_id}.json")
        if not os.path.exists(filepath):
            return {"messages": []}
        with open(filepath, 'r', encoding='utf-8') as f:
            chat_data = json.load(f)
        return chat_data
    
send_email_declaration={
    "name": "send_email",
    "description": "Send an email",
    "parameters": {
        "type": "object",
        "properties": {
            "to": {"type": "string"},
            "subject": {"type": "string"},
            "message": {"type": "string"}
        },
        "required": ["to", "subject", "message"]
    }
}
list_courses_declaration={
    "name": "list_courses",
    "description": "List all courses for the user. You can use this function to get the course_id",
    "parameters": {
        "type": "object",
        "properties": {
                
        },
        "required": []
    }
}
list_course_students_declaration={
    "name": "list_course_students",
    "description": "List all students for a course. You can use this function to get the student_id",
    "parameters": {
        "type": "object",
        "properties": {
            "course_id": {"type": "string"},
        },
        "required": ["course_id"]
    }
}
get_student_declaration={
    "name": "get_student",
    "description": "Get a student by id. You can use this function to get the student_id",
    "parameters": {
        "type": "object",
        "properties": {
            "course_id": {"type": "string"},
            "student_id": {"type": "string"},
        },
        "required": ["course_id", "student_id"]
    }
}
list_student_submissions_declaration={
    "name": "list_student_submissions",
    "description": "List all submissions for a student. You can use this function to get the coursework_id.if you want to access the submitted file,use the driveID in the response to download the file from Google Drive",
    "parameters": {
        "type": "object",
        "properties": {
            "course_id": {"type": "string"},
            "student_id": {"type": "string"},
        },
        "required": ["course_id", "student_id"]
    }
}
get_coursework_declaration={
    "name": "get_coursework",
    "description": "Get a coursework by id",
    "parameters": {
        "type": "object",
        "properties": {
            "course_id": {"type": "string"},
            "coursework_id": {"type": "string"},
        },
        "required": ["course_id", "coursework_id"]
    }
}
get_coursework_materials_declaration={
    "name": "get_coursework_materials",
    "description": "Get the materials for a coursework",
    "parameters": {
        "type": "object",
        "properties": {
            "course_id": {"type": "string"},
            "coursework_id": {"type": "string"},
        },
        "required": ["course_id", "coursework_id"]
    }
}
list_courseworks_declaration={
    "name": "list_courseworks",
    "description": "List all coursework for a course",
    "parameters": {
        "type": "object",
        "properties": {
            "course_id": {"type": "string"},
        },
        "required": ["course_id"]
    }
}
download_file_from_drive_and_upload_to_gemini_declaration={
    "name": "download_file_from_drive_and_upload_to_gemini",
    "description": "Download a file from Google Drive and upload it to Gemini. file_id can be fetched using list_courseworks(course_id) function",
    "parameters": {
        "type": "object",
        "properties": {
            "file_id": {"type": "string"},
        },
        "required": ["file_id"]
    }
}
summarize_file_from_gemini_declaration={
    "name": "summarize_file_from_gemini",
    "description": "Summarize a file that has been uploaded to Gemini. file_upload_response can be obtained from download_file_from_drive_and_upload_to_gemini function",
    "parameters": {
        "type": "object",
        "properties": {
            
           "file_uri": {"type": "string"},

        },
        "required": ["file_uri"]
    }
}
create_quiz_declaration={
    "name": "create_quiz",
    "description": "Create a quiz for a course. quiz_questions is a list of questions for the quiz. Each question is a dictionary with the following properties: question, options, isRequired, type, pointValue, correctAnswers ,type can be RADIO, CHECKBOX, DROPDOWN only",
    "parameters": {
        "type": "object",
        "properties": {
            "quiz_name": {"type": "string"},
            "quiz_description": {"type": "string"},
            "quiz_questions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "question": {"type": "string"},
                        "options": {
                            "type": "array", 
                            "items": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "string"}
                                },
                                "required": ["value"]
                            }
                        },
                        "isRequired": {"type": "boolean"},
                        "type": {"type": "string"},
                        "pointValue": {"type": "number"},
                        "correctAnswers": {
                            "type": "object",
                            "properties": {
                                "answers": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "value": {"type": "string"}
                                        },
                                        "required": ["value"]
                                    }
                                }
                            },
                            "required": ["answers"]
                        }
                    },
                    "required": ["question", "options", "isRequired", "type", "pointValue", "correctAnswers"]
                }
            },
        },
        "required": ["quiz_name", "quiz_description", "quiz_questions"]
    }
}
create_announcement_declaration={
    "name": "create_announcement",
    "description": "Create an announcement for a course. announcement_body is a dictionary with the following properties: course_id, materials, text",
    "parameters": {
        "type": "object",
        "properties": {
            "course_id": {"type": "string"},
            "announcement_body": {
                "type": "object",
                "properties": {
                    "course_id": {"type": "string"},
                    "text": {"type": "string"}
                },
                "required": ["course_id", "text"]
            },
            "materials": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "driveFile": {
                            "type": "object",
                            "properties": {
                                "driveFile": {"type": "object",
                                "properties": {
                                    "id": {"type": "string"},
                                    "title": {"type": "string"},
                                    "alternateLink": {"type": "string"}
                                },
                                "required": ["id", "title", "alternateLink"]
                                }
                            },
                            "required": ["driveFile"]
                        },
                        "link": {
                            "type": "object",
                            "properties": {
                                "url": {"type": "string"}
                            },
                            "required": ["url"]
                        }
                    }
                }
            }
        },
        "required": ["course_id", "announcement_body", "materials"]
    }
}
list_forms_declaration={
    "name": "list_forms",
    "description": "List all forms",
    "parameters": {
        "type": "object",
        "properties": {
        },
        "required": []
    }
}
get_form_declaration={
    "name": "get_form",
    "description": "Get details about a specific form",
    "parameters": {
        "type": "object",
        "properties": {
            "form_id": {"type": "string"},
        },
        "required": ["form_id"]
    }
}
list_form_responses_declaration={
    "name": "list_form_responses",
    "description": "List all responses for a specific form",
    "parameters": {
        "type": "object",
        "properties": {
            "form_id": {"type": "string"},
        },
        "required": ["form_id"]
    }
}
get_form_response_declaration={
    "name": "get_form_response",
    "description": "Get details about a specific response",
    "parameters": {
        "type": "object",
        "properties": {
            "form_id": {"type": "string"},
            "response_id": {"type": "string"},
        },
        "required": ["form_id", "response_id"]
    }
}
question_bank_generator_declaration={
    "name": "question_bank_generator",
    "description": "Generate a question bank for a course. You must create the actual questions yourself based on the course topic. Each section must have a part_label (like A, B, C, D), marks (number), and questions array. Each question must have 'q' (question text that you generate) and optionally 'image_ref' (REAL image URL that actually exists). CRITICAL: Generate real, educational questions - do not ask the user for questions. For images, only use real URLs that point to actual images, not example.com or fake URLs.",
    "parameters": {
        "type": "object",
        "properties": {
            "course_code": {"type": "string"},
            "course_name": {"type": "string"},
            "module_number": {"type": "number"},
            "sections": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "part_label": {"type": "string"},
                        "marks": {"type": "number"},
                        "questions": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "q": {"type": "string"},
                                    "image_ref": {"type": "string"}
                                }
                            }
                        }
                    },
                    "required": ["part_label", "marks", "questions"]
                }
            },
            "include_images": {"type": "boolean"},
            "dep": {"type": "string"}
        },
        "required": ["sections"]
    }
}
answer_key_generator_declaration={
    "name": "answer_key_generator",
    "description": "Generate a answer key for a course. You must create the actual answers yourself based on the course topic. Each section must have a part_label (like A, B, C, D), marks (number), and answers array. Each answer must have 'answer' (answer text that you generate) and optionally 'image_ref' (REAL image URL that actually exists). CRITICAL: Generate real, educational answers - do not ask the user for answers. For images, only use real URLs that point to actual images, not example.com or fake URLs.",
    "parameters": {
        "type": "object",
        "properties": {
            "course_code": {"type": "string"},
            "course_name": {"type": "string"},
            "module_number": {"type": "number"},
            "sections": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "part_label": {"type": "string"},
                        "marks": {"type": "number"},
                        "answers": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "question": {"type": "string"},
                                    "answer": {"type": "string"},
                                    "image_ref": {"type": "string"}
                                },
                                "required": ["question", "answer"]
                            }
                        }
                    },
                    "required": ["part_label", "marks", "answers"]
                }
            },
            "include_images": {"type": "boolean"},
            "dep": {"type": "string"}
        },
        "required": ["sections"]
    }
}
create_coursework_declaration={
    "name": "create_coursework",
    "description": "Create a coursework for a course. coursework_body is a dictionary with the following properties: course_id, coursework_body. if assigneeMode is INDIVIDUAL_STUDENTS, individualStudentsOptions is required and must be an array of student ids. if assigneeMode is ALL_STUDENTS, individualStudentsOptions is not required",
    "parameters": {
        "type": "object",
        "properties": {
            "course_id": {"type": "string"},
            "coursework_body": {"type": "object",
            "properties": {
                "courseId": {"type": "string"},
                "title": {"type": "string"},
                "description": {"type": "string"},
                "materials": {"type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "driveFile": {"type": "object",
                        "properties": {
                            "driveFile": {"type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "title":{"type": "string"},
                                "alternateLink": {"type": "string"}
                            },
                            "required": ["id", "title", "alternateLink"]
                            }
                        },
                        "required": ["driveFile"]
                        },
                        "link": {"type": "object",
                        "properties": {
                            "url": {"type": "string"}
                        }
                        }
                    }
                }
                },
                "state": {"type": "string",
                "enum": ["DRAFT", "PUBLISHED"]
                },
                "workType": {"type": "string",
                "enum": ["COURSE_WORK_TYPE_UNSPECIFIED", "ASSIGNMENT", "SHORT_ANSWER_QUESTION", "MULTIPLE_CHOICE_QUESTION"]
                },
                "dueDate": {"type": "object",
                "properties": {
                    "year": {"type": "number"},
                    "month": {"type": "number"},
                    "day": {"type": "number"}
                }
                },
                "dueTime": {"type": "object",
                "properties": {
                    "hours": {"type": "number"},
                    "minutes": {"type": "number"},
                    "seconds": {"type": "number"},
                    "nanos": {"type": "number"}
                }
                },
                "maxPoints": {"type": "number"},
                "submissionModificationMode": {"type": "string",
                "enum": ["MODIFIABLE_UNTIL_TURNED_IN", "MODIFIABLE"]
                },
                "assigneeMode": {"type": "string",
                "enum": ["INDIVIDUAL_STUDENTS", "ALL_STUDENTS"]
                },
                "individualStudentsOptions": {"type": "object",
                "properties": {
                    "studentIds": {"type": "array", "items": {"type": "string"}}
                }
                }
            },
            "required": ["courseId", "title", "description", "materials", "state", "workType", "dueDate", "dueTime", "maxPoints", "assigneeMode", "submissionModificationMode"]
        }
        },
        "required": ["course_id", "coursework_body"]
    }
}
tools=genai.types.Tool(function_declarations=[send_email_declaration,list_courses_declaration,list_course_students_declaration,get_student_declaration,list_student_submissions_declaration,get_coursework_declaration,get_coursework_materials_declaration,list_courseworks_declaration,download_file_from_drive_and_upload_to_gemini_declaration,summarize_file_from_gemini_declaration,create_quiz_declaration,create_announcement_declaration,list_forms_declaration,get_form_declaration,list_form_responses_declaration,get_form_response_declaration,question_bank_generator_declaration,create_coursework_declaration,answer_key_generator_declaration])
config = genai.types.GenerateContentConfig(tools=[tools])

app = create_app()
doc_search = DocSearch()
@app.route("/chat/threads", methods=["GET"])
def get_threads():
    try:
        threads = doc_search.get_chats()
        print(f"Returning {len(threads)} chat threads")
        return jsonify({"threads": threads})
    except Exception as e:
        print(f"Error in get_threads: {e}")
        return jsonify({"threads": [], "error": str(e)})

@app.route("/ingest", methods=["POST"])
def ingest():
    print("Ingesting docs...")
    try:
        if not request.is_json:
            return jsonify({"error": "Content-Type must be application/json"}), 400
        
        data = request.get_json()
        if not data or "docs" not in data:
            return jsonify({"error": "Missing 'docs' field in request body"}), 400
        
        docs = data["docs"]
        if not isinstance(docs, list) or len(docs) == 0:
            return jsonify({"error": "'docs' must be a non-empty list"}), 400
        
        doc_search.ingest_docs(docs)
        return jsonify({"message": "Documents ingested successfully", "count": len(docs)})
    
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500
    
@app.route("/query", methods=["POST"])
def search():
    try:
        # Check if request contains files (FormData) or is JSON
        if request.files:
            # Handle file upload with FormData
            query = request.form.get("query")
            chat_id = request.form.get("chat_id")
            user_id = str(request.form.get("user_id")) if request.form.get("user_id") else None
            k = int(request.form.get("k", 50))
            selected_folders = request.form.getlist("selected_folders")  # Get list of selected folders
            
            if not query or not query.strip():
                return jsonify({"error": "Missing or empty 'query' field"}), 400
            
            # Get uploaded files
            uploaded_files = []
            for key, file in request.files.items():
                if key.startswith("file_"):
                    uploaded_files.append(file)
            
            # Process with files - use selected folders if provided
            context = doc_search.get_context(query, k, selected_folders, user_id)
            response = doc_search.get_response_with_files(query, k, user_id, uploaded_files,selected_folders,chat_id)
            
        else:
            # Handle regular JSON request
            data = request.get_json()
            if not request.is_json:
                return jsonify({"error": "Content-Type must be application/json or multipart/form-data"}), 400
            
            chat_id = data.get("chat_id")
            user_id = str(data.get("user_id")) if data.get("user_id") else None
            query = data.get("query")
            k = data.get("k", 50)
            selected_folders = data.get("selected_folders", [])  # New parameter for selected libraries
            
            if not chat_id:
                chat_id = str(uuid.uuid4())
            
            if not query or not isinstance(query, str) or len(query.strip()) == 0:
                return jsonify({"error": "'query' must be a non-empty string"}), 400
            
            if not isinstance(k, int) or k <= 0:
                return jsonify({"error": "'k' must be a positive integer"}), 400
            
            # Use selected folders if provided, otherwise use general search
            context = None
            if selected_folders and len(selected_folders) > 0:
                context = doc_search.get_context(query, k, selected_folders, user_id)
                print(f"Context: {context}")
            
            response = doc_search.get_response(query, k, user_id, selected_folders,chat_id)
        
        chat_id = doc_search.add_to_chat(chat_id, {"role": "user", "content": query})
        doc_search.add_to_chat(chat_id, {"role": "assistant", "content": response})
        return jsonify({"query": query, "k": k, "context": context, "response": response, "chat_id": chat_id})
    
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@app.route("/", methods=["GET"])
def test():
    return jsonify({
        "message": "RAG API is running!", 
        "endpoints": [
            "/ingest (POST)", 
            "/query (POST)",
            "/files/upload (POST)",
            "/files/delete (DELETE)"
        ],
        "usage": {
            "ingest": {"docs": ["document1", "document2"]},
            "query": {"query": "your search query", "k": 5},
            "query_with_files": {"query": "your search query", "files": "multipart/form-data"}
        }
    })

@app.route("/files/upload", methods=["POST"])
def upload_file():
    """Upload a single file to Gemini Files API"""
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        from routes.ai_service import upload_to_gemini
        result = upload_to_gemini(file)
        
        if result["success"]:
            return jsonify({
                "message": "File uploaded successfully",
                "file_uri": result["uri"],
                "mime_type": result["mime_type"],
                "display_name": result["display_name"]
            })
        else:
            return jsonify({"error": result["error"]}), 500
            
    except Exception as e:
        return jsonify({"error": f"Upload failed: {str(e)}"}), 500

@app.route("/files/delete", methods=["DELETE"])
def delete_file():
    """Delete a file from Gemini Files API"""
    try:
        data = request.get_json()
        file_uri = data.get("file_uri")
        
        if not file_uri:
            return jsonify({"error": "file_uri is required"}), 400
        
        from routes.ai_service import delete_file_from_gemini
        result = delete_file_from_gemini(file_uri)
        
        if result["success"]:
            return jsonify({"message": "File deleted successfully"})
        else:
            return jsonify({"error": result["error"]}), 500
            
    except Exception as e:
        return jsonify({"error": f"Delete failed: {str(e)}"}), 500

@app.route("/ingest_file", methods=["POST"])
def ingest_file():
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 400
    data = request.get_json()
    file_path = data.get("file_path")
    return doc_search.ingest_file(file_path)

@app.route("/ingest_json",methods=["POST"])
def ingest_json():
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 400
    data = request.get_json()
    file_path = data.get("file_path")
    data=doc_search.extract_text_from_json(file_path)
    doc_search.ingest_docs([data])
    return jsonify({"message": "JSON ingested successfully", "count": 1})

@app.route("/reset_index",methods=['GET'])
def reset_index():
    doc_search.reset_index()
    return jsonify({"message": "Index reset successfully"})

# Chat management routes
@app.route("/chats", methods=["GET"])
def get_chats():
    """Get all chat histories"""
    try:
        chats = []
        for filename in os.listdir(CHAT_STORAGE_DIR):
            if filename.endswith('.json'):
                chat_id = filename[:-5]  # Remove .json extension
                filepath = os.path.join(CHAT_STORAGE_DIR, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    chat_data = json.load(f)
                    chats.append({
                        "id": chat_id,
                        "title": chat_data.get("title", "New Chat"),
                        "created_at": chat_data.get("created_at", ""),
                        "updated_at": chat_data.get("updated_at", "")
                    })
        
        # Sort by updated_at descending
        chats.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        return jsonify({"chats": chats})
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@app.route("/chats", methods=["POST"])
def create_chat():
    """Create a new chat"""
    try:
        chat_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        chat_data = {
            "id": chat_id,
            "title": "New Chat",
            "created_at": now,
            "updated_at": now,
            "messages": []
        }
        
        filepath = os.path.join(CHAT_STORAGE_DIR, f"{chat_id}.json")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(chat_data, f, indent=2)
        
        return jsonify({"chat": chat_data})
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@app.route("/chats/<chat_id>", methods=["GET"])
def get_chat(chat_id):
    """Get a specific chat by ID"""
    try:
        filepath = os.path.join(CHAT_STORAGE_DIR, f"{chat_id}.json")
        if not os.path.exists(filepath):
            return jsonify({"error": "Chat not found"}), 404
        
        with open(filepath, 'r', encoding='utf-8') as f:
            chat_data = json.load(f)
        
        return jsonify({"chat": chat_data})
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@app.route("/chats/<chat_id>/messages", methods=["POST"])
def add_message(chat_id):
    """Add a message to a chat"""
    try:
        data = request.get_json()
        message = data.get("message", "")
        role = data.get("role", "user")  # "user" or "assistant"
        
        if not message.strip():
            return jsonify({"error": "Message cannot be empty"}), 400
        
        filepath = os.path.join(CHAT_STORAGE_DIR, f"{chat_id}.json")
        if not os.path.exists(filepath):
            return jsonify({"error": "Chat not found"}), 404
        
        with open(filepath, 'r', encoding='utf-8') as f:
            chat_data = json.load(f)
        
        # Add new message
        new_message = {
            "id": str(uuid.uuid4()),
            "role": role,
            "content": message,
            "timestamp": datetime.now().isoformat()
        }
        
        chat_data["messages"].append(new_message)
        chat_data["updated_at"] = datetime.now().isoformat()
        
        # Update title if it's the first user message
        if role == "user" and chat_data["title"] == "New Chat":
            chat_data["title"] = message[:50] + "..." if len(message) > 50 else message
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(chat_data, f, indent=2)
        
        return jsonify({"message": new_message})
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@app.route("/chats/<chat_id>", methods=["DELETE"])
def delete_chat(chat_id):
    """Delete a chat"""
    try:
        filepath = os.path.join(CHAT_STORAGE_DIR, f"{chat_id}.json")
        if not os.path.exists(filepath):
            return jsonify({"error": "Chat not found"}), 404
        
        os.remove(filepath)
        return jsonify({"message": "Chat deleted successfully"})
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@app.route("/chat/query", methods=["POST"])
def chat_query():
    """Send a query and get AI response using RAG"""
    try:
        data = request.get_json()
        query = data.get("query", "")
        chat_id = data.get("chat_id")
        user_id = data.get("user_id")
        selected_folders = data.get("selected_folders", [])
        
        if not query.strip():
            return jsonify({"error": "Query cannot be empty"}), 400
        
        # Get AI response using existing RAG system with selected folders
        # Only get context if selected folders are provided
        context = None
        if selected_folders and len(selected_folders) > 0:
            context = doc_search.get_context(query, k=12, selected_folders=selected_folders, user_id=user_id)
        
        response = doc_search.get_response(query, k=12, user_id=user_id, selected_folders=selected_folders, chat_id=chat_id)
        
        # If chat_id provided, save the conversation
        if chat_id:
            # Save user message
            add_message(chat_id, query, "user")
            
            # Save assistant response
            filepath = os.path.join(CHAT_STORAGE_DIR, f"{chat_id}.json")
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    chat_data = json.load(f)
                
                assistant_message = {
                    "id": str(uuid.uuid4()),
                    "role": "assistant",
                    "content": response,
                    "timestamp": datetime.now().isoformat()
                }
                
                chat_data["messages"].append(assistant_message)
                chat_data["updated_at"] = datetime.now().isoformat()
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(chat_data, f, indent=2)
        
        return jsonify({
            "query": query,
            "response": response,
            "context": context
        })
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

if __name__ == "__main__":
    secret_key = os.getenv("FLASK_SECRET_KEY")
    if not secret_key:
        raise ValueError("FLASK_SECRET_KEY environment variable is required. Set it in your .env file.")
    app.secret_key = secret_key
    port = int(os.getenv("FLASK_PORT", "5001"))
    debug_mode = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    app.run(debug=debug_mode, port=port)



 
