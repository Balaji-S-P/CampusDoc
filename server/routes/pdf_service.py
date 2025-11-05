import os
import requests
from io import BytesIO
from fpdf import FPDF
from routes.drive_service import get_drive_service,upload_local_file_to_drive
import uuid
import re

def clean_text_for_pdf(text):
    """Clean text to remove or replace Unicode characters that cause encoding issues"""
    if not text:
        return ""
    
    # Replace common Unicode characters with ASCII equivalents
    replacements = {
        '\u2013': '-',  # en-dash
        '\u2014': '--', # em-dash
        '\u2018': "'",  # left single quotation mark
        '\u2019': "'",  # right single quotation mark
        '\u201c': '"',  # left double quotation mark
        '\u201d': '"',  # right double quotation mark
        '\u2026': '...', # horizontal ellipsis
        '\u00a0': ' ',  # non-breaking space
    }
    
    for unicode_char, ascii_char in replacements.items():
        text = text.replace(unicode_char, ascii_char)
    
    # Remove any remaining non-ASCII characters that might cause issues
    text = re.sub(r'[^\x00-\x7F]+', '?', text)
    
    return text
def question_bank_generator(course_code: str = None,
    course_name: str = None,
    module_number: int = None,
    sections: list = None,  # [{"part_label": "A", "marks": 10, "questions": [{"q": "...", "image_ref": "..."}]}]
    include_images: bool = False,
    dep: str = None,
    user_id: str = None):
    """
    Generate a question bank PDF and upload it to Google Drive.
    
    Args:
        course_code: Course code (e.g., "CS101")
        course_name: Course name (e.g., "Introduction to Computer Science")
        module_number: Module number
        sections: List of sections with questions
        include_images: Whether to include images in the PDF
        dep: Department name
        user_id: User ID for authentication
    
    Returns:
        dict: A dictionary containing:
            - "success": bool
            - "message": str
            - "file_id": str
            - "webViewLink": str
    
    sections format:
    [
        {
            "part_label": "A",
            "marks": 10,
            "questions": [
                {
                    "q": "What is the capital of France?",
                    "image_ref": "https://example.com/image.png"
                }
            ]
        }
    ]
    """
    try:
        # Validate sections data
        if not sections:
            return {"error": "No sections provided"}
        
        # Check if questions have content
        empty_questions_count = 0
        for section in sections:
            questions = section.get("questions", [])
            for question in questions:
                if not question.get('q', '').strip():
                    empty_questions_count += 1
        
        if empty_questions_count > 0:
            print(f"Warning: {empty_questions_count} questions have no content")
        
        service = get_drive_service(user_id)
        if isinstance(service, dict) and "error" in service:
            return service
        pdf = FPDF()
        pdf_filename = str(uuid.uuid4())
        if course_code and course_name and module_number:
            pdf_filename = f"{course_code}_Module{module_number}_QuestionBank.pdf"
        pdf_path = f"/tmp/{pdf_filename}.pdf"
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)
        
        # Header
        pdf.set_font("Arial", "B", 14)
        if dep:
            pdf.cell(0, 10, clean_text_for_pdf(f"Department of {dep}"), ln=True, align="C")
        if course_code and course_name:
            pdf.cell(0, 10, clean_text_for_pdf(f"{course_code} - {course_name}"), ln=True, align="C")
        if module_number:
            pdf.cell(0, 10, clean_text_for_pdf(f"Module {module_number} Question Bank"), ln=True, align="C")
        pdf.ln(10)
        
        # Loop through sections
        for section in sections:
            part_label = section.get("part_label", "")
            marks = section.get("marks", 0)
            questions = section.get("questions", [])
            
            # Section Header
            pdf.set_font("Arial", "B", 12)
            pdf.cell(0, 10, clean_text_for_pdf(f"Part - {part_label} ({marks} marks)"), ln=True)
            pdf.set_font("Arial", "", 11)
            
            # Loop through questions
            for i, question in enumerate(questions, 1):
                question_text = clean_text_for_pdf(question.get('q', ''))
                if not question_text.strip():
                    question_text = f"[Question {i} - No content provided]"
                pdf.multi_cell(0, 8, f"{i}. {question_text}")
                
                # Include image if required
                if include_images and question.get("image_ref"):
                    image_url = question.get("image_ref", "").strip()
                    print(f"Processing image for question {i}: {image_url}")
                    
                    # Check for common fake/example URLs
                    fake_domains = ['example.com', 'example.org', 'placeholder.com', 'via.placeholder.com', 'dummyimage.com']
                    is_fake_url = any(domain in image_url.lower() for domain in fake_domains)
                    
                    if is_fake_url:
                        print(f"Skipping fake URL: {image_url}")
                        error_text = clean_text_for_pdf(f"[Note: Image reference appears to be a placeholder URL and was skipped]")
                        pdf.cell(0, 8, error_text, ln=True)
                    elif image_url and image_url.startswith(('http://', 'https://')):
                        try:
                            # Download image with proper headers
                            headers = {
                                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                            }
                            response = requests.get(image_url, headers=headers, timeout=10)
                            response.raise_for_status()
                            
                            # Determine file extension from content type or URL
                            content_type = response.headers.get('content-type', '').lower()
                            if 'jpeg' in content_type or 'jpg' in content_type:
                                ext = '.jpg'
                            elif 'png' in content_type:
                                ext = '.png'
                            elif 'gif' in content_type:
                                ext = '.gif'
                            else:
                                # Try to determine from URL
                                if image_url.lower().endswith(('.jpg', '.jpeg')):
                                    ext = '.jpg'
                                elif image_url.lower().endswith('.png'):
                                    ext = '.png'
                                elif image_url.lower().endswith('.gif'):
                                    ext = '.gif'
                                else:
                                    ext = '.jpg'  # Default fallback
                            
                            # Save to temporary file
                            temp_image_path = f"/tmp/temp_image_{i}_{part_label}{ext}"
                            with open(temp_image_path, "wb") as f:
                                f.write(response.content)
                            
                            # Add image to PDF with better sizing
                            pdf.ln(2)  # Add some space before image
                            pdf.image(temp_image_path, w=150, h=100)  # Better default size
                            pdf.ln(2)  # Add some space after image
                            
                            print(f"Successfully added image for question {i}")
                            
                            # Clean up temporary file
                            os.remove(temp_image_path)
                            
                        except requests.exceptions.RequestException as e:
                            error_text = clean_text_for_pdf(f"[Image download failed: {str(e)}]")
                            pdf.cell(0, 8, error_text, ln=True)
                        except Exception as e:
                            error_text = clean_text_for_pdf(f"[Image processing failed: {str(e)}]")
                            pdf.cell(0, 8, error_text, ln=True)
                    else:
                        # Invalid URL format
                        error_text = clean_text_for_pdf(f"[Invalid image URL: {image_url}]")
                        pdf.cell(0, 8, error_text, ln=True)
            
            pdf.ln(5)
        pdf.output(pdf_path)
        upload_result = upload_local_file_to_drive(pdf_path, user_id, "application/pdf")
        if isinstance(upload_result, dict) and "error" in upload_result:
            return upload_result
        return {
            "success": True,
            "message": "Question bank generated successfully",
            "file_id": upload_result.get("file_id"),
            "webViewLink": upload_result.get("webViewLink")
        }
    except Exception as e:
        return {"error": f"Failed to generate question bank: {str(e)}"}

def answer_key_generator(course_code: str = None,
    course_name: str = None,
    module_number: int = None,
    sections: list = None,  # [{"part_label": "A", "marks": 10, "answers": [{"question": "...", "answer": "...", "image_ref": "..."}]}]
    include_images: bool = False,
    dep: str = None,
    user_id: str = None):
    """
    Generate a answer key PDF and upload it to Google Drive.
    
    Args:
        course_code: Course code (e.g., "CS101")
        course_name: Course name (e.g., "Introduction to Computer Science")
        module_number: Module number
        sections: List of sections with answers
        include_images: Whether to include images in the PDF
        dep: Department name
        user_id: User ID for authentication
    
    Returns:
        dict: A dictionary containing:
            - "success": bool
            - "message": str
            - "file_id": str
            - "webViewLink": str
    
    sections format:
    [
        {
            "part_label": "A",
            "marks": 10,
            "answers": [
                {
                    "question": "What is the capital of France?",
                    "answer": "What is the capital of France?",
                    "image_ref": "https://example.com/image.png"
                }
            ]
        }
    ]
    """
    try:
        # Validate sections data
        if not sections:
            return {"error": "No sections provided"}
        
        # Check if answers have content
        empty_answers_count = 0
        empty_questions_count = 0
        for section in sections:
            answers = section.get("answers", [])
            for answer in answers:
                if not answer.get('answer', '').strip():
                    empty_answers_count += 1
                if not answer.get('question', '').strip():
                    empty_questions_count += 1
        
        if empty_answers_count > 0:
            print(f"Warning: {empty_answers_count} answers have no content")
        if empty_questions_count > 0:
            print(f"Warning: {empty_questions_count} questions have no content")
        service = get_drive_service(user_id)
        if isinstance(service, dict) and "error" in service:
            return service
        pdf = FPDF()
        pdf_filename = str(uuid.uuid4())
        if course_code and course_name and module_number:
            pdf_filename = f"{course_code}_Module{module_number}_AnswerKey.pdf"
        pdf_path = f"/tmp/{pdf_filename}.pdf"
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)
        
        # Header
        pdf.set_font("Arial", "B", 14)
        if dep:
            pdf.cell(0, 10, clean_text_for_pdf(f"Department of {dep}"), ln=True, align="C")
        if course_code and course_name:
            pdf.cell(0, 10, clean_text_for_pdf(f"{course_code} - {course_name}"), ln=True, align="C")
        if module_number:
            pdf.cell(0, 10, clean_text_for_pdf(f"Module {module_number} Answer Key"), ln=True, align="C")
        pdf.ln(10)
        
        # Loop through sections
        for section in sections:
            part_label = section.get("part_label", "")
            marks = section.get("marks", 0)
            answers = section.get("answers", [])
            
            # Section Header
            pdf.set_font("Arial", "B", 12)
            pdf.cell(0, 10, clean_text_for_pdf(f"Part - {part_label} ({marks} marks)"), ln=True)
            pdf.set_font("Arial", "", 11)
            
            # Loop through questions
            for i, answer in enumerate(answers, 1):
                question_text = clean_text_for_pdf(answer.get('question', ''))
                if not question_text.strip():
                    question_text = f"[Question {i} - No content provided]"
                pdf.multi_cell(0, 8, f"{i}. {question_text}")
                answer_text = clean_text_for_pdf(answer.get('answer', ''))
                if not answer_text.strip():
                    answer_text = f"[Answer {i} - No content provided]"
                pdf.multi_cell(0, 8, f"Answer: {answer_text}")
                
                # Include image if required
                if include_images and answer.get("image_ref"):
                    image_url = answer.get("image_ref", "").strip()
                    print(f"Processing image for question {i}: {image_url}")
                    
                    # Check for common fake/example URLs
                    fake_domains = ['example.com', 'example.org', 'placeholder.com', 'via.placeholder.com', 'dummyimage.com']
                    is_fake_url = any(domain in image_url.lower() for domain in fake_domains)
                    
                    if is_fake_url:
                        print(f"Skipping fake URL: {image_url}")
                        error_text = clean_text_for_pdf(f"[Note: Image reference appears to be a placeholder URL and was skipped]")
                        pdf.cell(0, 8, error_text, ln=True)
                    elif image_url and image_url.startswith(('http://', 'https://')):
                        try:
                            # Download image with proper headers
                            headers = {
                                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                            }
                            response = requests.get(image_url, headers=headers, timeout=10)
                            response.raise_for_status()
                            
                            # Determine file extension from content type or URL
                            content_type = response.headers.get('content-type', '').lower()
                            if 'jpeg' in content_type or 'jpg' in content_type:
                                ext = '.jpg'
                            elif 'png' in content_type:
                                ext = '.png'
                            elif 'gif' in content_type:
                                ext = '.gif'
                            else:
                                # Try to determine from URL
                                if image_url.lower().endswith(('.jpg', '.jpeg')):
                                    ext = '.jpg'
                                elif image_url.lower().endswith('.png'):
                                    ext = '.png'
                                elif image_url.lower().endswith('.gif'):
                                    ext = '.gif'
                                else:
                                    ext = '.jpg'  # Default fallback
                            
                            # Save to temporary file
                            temp_image_path = f"/tmp/temp_image_{i}_{part_label}{ext}"
                            with open(temp_image_path, "wb") as f:
                                f.write(response.content)
                            
                            # Add image to PDF with better sizing
                            pdf.ln(2)  # Add some space before image
                            pdf.image(temp_image_path, w=150, h=100)  # Better default size
                            pdf.ln(2)  # Add some space after image
                            
                            print(f"Successfully added image for answer {i}")
                            
                            # Clean up temporary file
                            os.remove(temp_image_path)
                            
                        except requests.exceptions.RequestException as e:
                            error_text = clean_text_for_pdf(f"[Image download failed: {str(e)}]")
                            pdf.cell(0, 8, error_text, ln=True)
                        except Exception as e:
                            error_text = clean_text_for_pdf(f"[Image processing failed: {str(e)}]")
                            pdf.cell(0, 8, error_text, ln=True)
                    else:
                        # Invalid URL format
                        error_text = clean_text_for_pdf(f"[Invalid image URL: {image_url}]")
                        pdf.cell(0, 8, error_text, ln=True)
            
            pdf.ln(5)
        pdf.output(pdf_path)
        upload_result = upload_local_file_to_drive(pdf_path, user_id, "application/pdf")
        if isinstance(upload_result, dict) and "error" in upload_result:
            return upload_result
        return {
            "success": True,
            "message": "Answer key generated successfully",
            "file_id": upload_result.get("file_id"),
            "webViewLink": upload_result.get("webViewLink")
        }
    except Exception as e:
        return {"error": f"Failed to generate answer key: {str(e)}"}
    
    