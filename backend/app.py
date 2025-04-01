from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import db
import openai
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Initialize OpenAI client
openai.api_key = os.environ.get("OPENAI_API_KEY")

# Authentication routes
@app.route('/api/auth/signup', methods=['POST'])
def signup():
    data = request.json
    try:
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({"error": "Email and password are required"}), 400
            
        # Call Supabase signup
        response = db.sign_up(email, password)
        
        # Return user data in the expected format
        return jsonify({
            "user": response.user.dict() if response.user else None,
            "session": response.session.dict() if response.session else None
        }), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/auth/signin', methods=['POST'])
def signin():
    data = request.json
    try:
        email = data.get('email')
        password = data.get('password')
        response = db.sign_in(email, password)
        return jsonify(response.dict()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/auth/signout', methods=['POST'])
def signout():
    try:
        db.sign_out()
        return jsonify({"message": "Successfully signed out"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/auth/reset-password', methods=['POST'])
def reset_password():
    data = request.json
    try:
        email = data.get('email')
        db.reset_password(email)
        return jsonify({"message": "Password reset email sent"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# Add session route
@app.route('/api/auth/session', methods=['GET'])
def session():
    try:
        # Get session from request headers
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({"error": "No authorization header"}), 401
            
        # Verify session with Supabase
        session = db.supabase.auth.get_session()
        return jsonify({
            "session": session.dict() if session else None
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 401

# Conference routes
@app.route('/api/conferences', methods=['GET'])
def get_conferences():
    try:
        user_id = request.headers.get('user-id')
        if not user_id:
            return jsonify({"error": "User ID required"}), 400
        
        response = db.get_conferences(user_id)
        return jsonify(response.data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/conferences/<int:conference_id>', methods=['GET'])
def get_conference(conference_id):
    try:
        user_id = request.headers.get('user-id')
        if not user_id:
            return jsonify({"error": "User ID required"}), 400
        
        response = db.get_conference(conference_id, user_id)
        return jsonify(response.data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/conferences', methods=['POST'])
def create_conference():
    try:
        user_id = request.headers.get('user-id')
        if not user_id:
            return jsonify({"error": "User ID required"}), 400
        
        data = request.json
        response = db.create_conference(user_id, data)
        
        # Update user stats
        stats = db.get_user_stats(user_id).data
        db.update_user_stats(user_id, {
            "conferences_count": stats.get("conferences_count", 0) + 1
        })
        
        return jsonify(response.data), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/conferences/<int:conference_id>', methods=['PUT'])
def update_conference(conference_id):
    try:
        user_id = request.headers.get('user-id')
        if not user_id:
            return jsonify({"error": "User ID required"}), 400
        
        data = request.json
        response = db.update_conference(conference_id, user_id, data)
        return jsonify(response.data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/conferences/<int:conference_id>', methods=['DELETE'])
def delete_conference(conference_id):
    try:
        user_id = request.headers.get('user-id')
        if not user_id:
            return jsonify({"error": "User ID required"}), 400
        
        response = db.delete_conference(conference_id, user_id)
        
        # Update user stats
        stats = db.get_user_stats(user_id).data
        if stats.get("conferences_count", 0) > 0:
            db.update_user_stats(user_id, {
                "conferences_count": stats.get("conferences_count") - 1
            })
        
        return jsonify(response.data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# Document routes
@app.route('/api/documents', methods=['GET'])
def get_documents():
    try:
        user_id = request.headers.get('user-id')
        if not user_id:
            return jsonify({"error": "User ID required"}), 400
        
        response = db.get_documents(user_id)
        return jsonify(response.data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/documents/<int:document_id>', methods=['GET'])
def get_document(document_id):
    try:
        user_id = request.headers.get('user-id')
        if not user_id:
            return jsonify({"error": "User ID required"}), 400
        
        response = db.get_document(document_id, user_id)
        return jsonify(response.data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/documents', methods=['POST'])
def create_document():
    try:
        user_id = request.headers.get('user-id')
        if not user_id:
            return jsonify({"error": "User ID required"}), 400
        
        data = request.json
        response = db.create_document(user_id, data)
        
        # Update user stats
        stats = db.get_user_stats(user_id).data
        db.update_user_stats(user_id, {
            "documents_count": stats.get("documents_count", 0) + 1
        })
        
        return jsonify(response.data), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/documents/<int:document_id>', methods=['PUT'])
def update_document(document_id):
    try:
        user_id = request.headers.get('user-id')
        if not user_id:
            return jsonify({"error": "User ID required"}), 400
        
        data = request.json
        response = db.update_document(document_id, user_id, data)
        return jsonify(response.data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/documents/<int:document_id>', methods=['DELETE'])
def delete_document(document_id):
    try:
        user_id = request.headers.get('user-id')
        if not user_id:
            return jsonify({"error": "User ID required"}), 400
        
        response = db.delete_document(document_id, user_id)
        
        # Update user stats
        stats = db.get_user_stats(user_id).data
        if stats.get("documents_count", 0) > 0:
            db.update_user_stats(user_id, {
                "documents_count": stats.get("documents_count") - 1
            })
        
        return jsonify(response.data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# User stats routes
@app.route('/api/user-stats', methods=['GET'])
def get_stats():
    try:
        user_id = request.headers.get('user-id')
        if not user_id:
            return jsonify({"error": "User ID required"}), 400
        
        response = db.get_user_stats(user_id)
        return jsonify(response.data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/user-stats/awards', methods=['PUT'])
def update_awards():
    try:
        user_id = request.headers.get('user-id')
        if not user_id:
            return jsonify({"error": "User ID required"}), 400
        
        data = request.json
        awards_count = data.get('awards_count')
        
        response = db.update_user_stats(user_id, {
            "awards_count": awards_count
        })
        
        return jsonify(response.data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# AI routes
@app.route('/api/ai/generate-position-paper', methods=['POST'])
def generate_position_paper():
    """
    Generate a position paper using OpenAI API.
    Requires user-id in headers and structured request body.
    Returns generated paper content and created document.
    """
    # Validate OpenAI API key presence
    if not openai.api_key:
        return jsonify({"error": "Server configuration error: OpenAI API key not found"}), 500
    
    try:
        # Validate user authentication
        user_id = request.headers.get('user-id')
        if not user_id:
            return jsonify({"error": "Authentication required", "details": "User ID header is missing"}), 401
        
        # Parse and validate request body
        if not request.json:
            return jsonify({"error": "Invalid request", "details": "Request body must be JSON"}), 400
            
        data = request.json
        
        # Validate required fields
        required_fields = ['country', 'committee', 'topic', 'conference']
        missing_fields = [field for field in required_fields if not data.get(field)]
        
        if missing_fields:
            return jsonify({
                "error": "Missing required fields", 
                "details": f"The following fields are required: {', '.join(missing_fields)}"
            }), 400
        
        # Extract data for prompt with defaults for optional fields
        conference = data.get('conference', '')
        committee = data.get('committee', '')
        topic = data.get('topic', '')
        country = data.get('country', '')
        template = data.get('template', 'Standard Position Paper')
        background_text = data.get('background_text', '')
        custom_requirements = data.get('custom_requirements', '')
        
        # Log request information
        app.logger.info(f"Generating position paper for user {user_id}: {country} in {committee} on {topic}")
            
        # Construct prompt
        prompt = f"""
            Create a formal position paper for a Model United Nations conference with the following details:
            
            CONFERENCE: {conference}
            COMMITTEE: {committee}
            TOPIC: {topic}
            COUNTRY: {country}
            
            FORMAT:
            1. Introduction with country background
            2. Country's position on the topic
            3. Past international actions
            4. Proposed solutions
            5. Conclusion
            
            STYLE GUIDELINES:
            - Formal and diplomatic language
            - Clear and well-structured paragraphs
            - Factual and accurate information
            - Professional tone appropriate for Model UN
            
            ADDITIONAL INFORMATION:
            {background_text}
            
            CUSTOM REQUIREMENTS:
            {custom_requirements}
            
            The paper should be approximately 800-1000 words.
        """
        
        # Make the OpenAI API call with explicit error handling
        try:
            response = openai.chat.completions.create(
                model="gpt-4o-mini",  # Use a reliable model
                messages=[
                    {"role": "system", "content": "You are an expert assistant that helps students write high-quality position papers for Model United Nations conferences."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000,
                timeout=30  # Add timeout to prevent hanging
            )
            
            # Validate response
            if not response or not response.choices or len(response.choices) == 0:
                return jsonify({"error": "Empty response from AI model"}), 500
                
            # Extract the generated text
            generated_text = response.choices[0].message.content
            
            # Validate generated content
            if not generated_text or len(generated_text) < 100:
                return jsonify({"error": "Generated content too short or empty"}), 500
            
            # Create document in database
            try:
                document_data = {
                    "title": f"{country} - {topic}",
                    "type": "Position Paper",
                    "committee": committee,
                    "conference": conference,
                    "content": generated_text,
                    "progress": 100,
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat()
                }
                
                document_response = db.create_document(user_id, document_data)
                
                # Update user stats if document created successfully
                if document_response and document_response.data:
                    try:
                        stats = db.get_user_stats(user_id).data
                        if stats:
                            db.update_user_stats(user_id, {
                                "documents_count": stats.get("documents_count", 0) + 1
                            })
                    except Exception as stats_err:
                        app.logger.error(f"Error updating user stats: {str(stats_err)}")
                        # Continue even if stats update fails
                
                # Return success response
                return jsonify({
                    "document": document_response.data[0] if document_response.data else None,
                    "content": generated_text
                }), 201
                
            except Exception as db_err:
                app.logger.error(f"Database error: {str(db_err)}")
                # If DB operation fails, still return the generated content
                return jsonify({
                    "content": generated_text,
                    "warning": "Document was generated but could not be saved to database"
                }), 200
                
        except Exception as openai_err:
            app.logger.error(f"OpenAI API error: {str(openai_err)}")
            return jsonify({"error": f"AI service error: {str(openai_err)}"}), 503
            
    except Exception as e:
        app.logger.error(f"Unexpected error in generate_position_paper: {str(e)}")
        return jsonify({"error": "Server error", "details": str(e)}), 500

# New optimized endpoint for document generation
@app.route('/api/ai/generate-document', methods=['POST'])
def generate_document():
    """
    Unified endpoint for generating all document types (position paper, resolution, speech)
    Implements rate limiting and robust error handling
    """
    # Validate OpenAI API key presence
    if not openai.api_key:
        return jsonify({"error": "Server configuration error: OpenAI API key not found"}), 500
    
    try:
        # Validate user authentication
        user_id = request.headers.get('user-id')
        if not user_id:
            return jsonify({"error": "Authentication required", "details": "User ID header is missing"}), 401
        
        # Parse request body - support both JSON and form data
        data = {}
        reference_texts = []
        
        if request.is_json:
            data = request.json
            # Extract fields from JSON
            document_type = data.get('document_type', 'position_paper')
            committee = data.get('committee', '')
            country = data.get('country', '')
            topic = data.get('topic', '')
            additional_context = data.get('additional_context', '')
        elif request.form:
            # Extract fields from form data
            data = request.form.to_dict()
            document_type = data.get('document_type', 'position_paper')
            committee = data.get('committee', '')
            country = data.get('country', '')
            topic = data.get('topic', '')
            additional_context = data.get('additional_context', '')
            
            # Handle reference materials if files uploaded
            if 'reference_materials' in request.files:
                reference_files = request.files.getlist('reference_materials')
                
                # Validate file count
                if len(reference_files) > 3:
                    return jsonify({
                        "error": "Too many files", 
                        "details": "Maximum 3 reference files allowed"
                    }), 400
                
                # Process each file
                for file in reference_files:
                    # Validate file size (5MB max)
                    file_data = file.read()
                    if len(file_data) > 5 * 1024 * 1024:
                        return jsonify({
                            "error": "File too large", 
                            "details": f"File {file.filename} exceeds 5MB limit"
                        }), 400
                    
                    # Extract text from file
                    try:
                        from utils.document_parser import extract_text_from_file
                        text = extract_text_from_file(file_data, file.content_type)
                        if text:
                            reference_texts.append(f"--- Content from {file.filename} ---\n{text}")
                    except Exception as e:
                        app.logger.error(f"Error extracting text from {file.filename}: {str(e)}")
                        # Continue even if one file fails
        else:
            return jsonify({
                "error": "Invalid request", 
                "details": "Request must be either JSON or multipart form data"
            }), 400
            
        # Validate required fields
        if not committee or not country or not topic:
            return jsonify({
                "error": "Missing required fields", 
                "details": "Committee, country, and topic are required"
            }), 400
        
        # Apply rate limiting
        # For a real implementation, use a proper rate limiting library or Redis
        # This is a simplified version
        from datetime import datetime, timedelta
        
        # Get user's rate limit data from database or create default
        rate_data = db.get_user_rate_limits(user_id).data
        if not rate_data:
            rate_data = {
                "user_id": user_id,
                "minute_count": 0,
                "minute_reset": (datetime.now() + timedelta(minutes=1)).isoformat(),
                "day_count": 0,
                "day_reset": (datetime.now() + timedelta(days=1)).isoformat()
            }
        
        # Check minute limit
        now = datetime.now()
        minute_reset = datetime.fromisoformat(rate_data.get("minute_reset", now.isoformat()))
        if now > minute_reset:
            # Reset minute counter
            rate_data["minute_count"] = 0
            rate_data["minute_reset"] = (now + timedelta(minutes=1)).isoformat()
        
        if rate_data["minute_count"] >= 3:
            time_remaining = max(0, (minute_reset - now).total_seconds())
            return jsonify({
                "error": "Rate limit exceeded", 
                "details": f"Maximum 3 requests per minute. Please try again in {int(time_remaining)} seconds.",
                "retry_after": int(time_remaining)
            }), 429
        
        # Check day limit
        day_reset = datetime.fromisoformat(rate_data.get("day_reset", now.isoformat()))
        if now > day_reset:
            # Reset day counter
            rate_data["day_count"] = 0
            rate_data["day_reset"] = (now + timedelta(days=1)).isoformat()
        
        if rate_data["day_count"] >= 30:
            time_remaining = max(0, (day_reset - now).total_seconds())
            hours = int(time_remaining // 3600)
            minutes = int((time_remaining % 3600) // 60)
            return jsonify({
                "error": "Daily rate limit exceeded", 
                "details": f"Maximum 30 requests per day. Limit resets in {hours}h {minutes}m.",
                "retry_after": int(time_remaining)
            }), 429
        
        # Log generation request
        app.logger.info(f"Generating {document_type} for user {user_id}: {country} in {committee} on {topic}")
        
        # Generate document based on type
        try:
            # Prepare the prompt based on document type
            if document_type == 'position_paper':
                system_prompt = """You are an expert Model UN advisor helping a high school student create a position paper. 
                Create a formal, well-researched position paper following standard Model UN format. 
                The paper should be 2-3 pages (about 1000-1500 words) and include:
                
                1. A header with committee name, country, and topic
                2. An introduction that states the country's position on the topic
                3. A body that outlines 2-3 specific policy proposals with supporting evidence
                4. A conclusion summarizing the country's stance and proposed solutions
                
                Use formal diplomatic language appropriate for Model UN. Include specific policies and actions 
                that align with the country's actual foreign policy and national interests. If background 
                information is provided, incorporate relevant details from it.
                
                Format the document with proper HTML tags for headings, paragraphs, and lists."""
                
                title = f"Position Paper: {country} on {topic}"
                
            elif document_type == 'resolution':
                system_prompt = """You are an expert Model UN advisor helping a high school student create a resolution paper.
                Create a formal UN-style resolution following proper formatting standards. Include:
                
                1. A header with the committee and topic
                2. Preambulatory clauses that describe the background and context
                3. Operative clauses that outline specific actions and solutions
                
                Use formal language with appropriate clause beginnings (e.g., "Recalling," "Deeply concerned," for preambulatory; 
                "Requests," "Decides," for operative). Number all operative clauses and use proper indentation.
                If background information is provided, incorporate relevant details.
                
                Format the resolution with proper HTML tags to maintain the standard UN resolution format."""
                
                title = f"Resolution: {topic} ({country})"
                
            else:  # speech
                system_prompt = """You are an expert Model UN advisor helping a high school student create a formal speech.
                Create a well-structured, engaging speech suitable for delivery in a Model UN committee. The speech should:
                
                1. Begin with appropriate committee greeting
                2. Clearly state the country's position on the topic
                3. Provide 2-3 key arguments supported by evidence
                4. End with a call to action and appropriate closing
                
                Keep the speech concise (approximately 500-700 words for a 3-4 minute delivery).
                Use diplomatic language appropriate for Model UN. If background information is provided,
                incorporate relevant details that support the country's position.
                
                Format the speech with proper HTML tags for paragraphs and emphasize key points."""
                
                title = f"Speech: {country} on {topic}"
            
            # Combine reference materials if any
            background_text = "\n\n".join(reference_texts) if reference_texts else ""
            if background_text and len(background_text) > 6000:
                background_text = background_text[:6000] + "... [text truncated for length]"
            
            # Construct the user prompt
            user_prompt = f"Committee: {committee}\nCountry: {country}\nTopic: {topic}\n"
            
            if background_text:
                user_prompt += f"\nBackground Information:\n{background_text}\n"
            
            if additional_context:
                user_prompt += f"\nAdditional Context:\n{additional_context}\n"
                
            user_prompt += f"\nPlease generate a complete {document_type.replace('_', ' ')} in HTML format."
            
            # Make API call with timeout and error handling
            try:
                # Use gpt-3.5-turbo for production to manage costs
                model = "gpt-3.5-turbo"
                
                response = openai.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    max_tokens=2048,
                    temperature=0.7,
                    timeout=45  # 45 second timeout
                )
                
                # Validate response
                if not response or not response.choices or len(response.choices) == 0:
                    return jsonify({"error": "Empty response from AI model"}), 500
                    
                # Extract the generated text
                generated_text = response.choices[0].message.content
                
                # Validate generated content
                if not generated_text or len(generated_text) < 100:
                    return jsonify({"error": "Generated content too short or empty"}), 500
                
                # Add wrapper div for styling if needed
                html_content = f"<div class='{document_type.replace('_', '-')}'>{generated_text}</div>"
                
                # Create document in database
                try:
                    document_data = {
                        "title": title,
                        "type": document_type.replace('_', ' ').title(),
                        "committee": committee,
                        "content": html_content,
                        "progress": 100,
                        "created_at": datetime.now().isoformat(),
                        "updated_at": datetime.now().isoformat()
                    }
                    
                    document_response = db.create_document(user_id, document_data)
                    
                    # Update rate limits
                    rate_data["minute_count"] += 1
                    rate_data["day_count"] += 1
                    db.update_user_rate_limits(user_id, rate_data)
                    
                    # Update user stats if document created successfully
                    if document_response and document_response.data:
                        try:
                            stats = db.get_user_stats(user_id).data
                            if stats:
                                db.update_user_stats(user_id, {
                                    "documents_count": stats.get("documents_count", 0) + 1
                                })
                        except Exception as stats_err:
                            app.logger.error(f"Error updating user stats: {str(stats_err)}")
                    
                    # Return success response with rate limit headers
                    document_id = document_response.data[0]['id'] if document_response.data else None
                    
                    response_obj = {
                        "document_id": document_id,
                        "content": html_content,
                        "title": title,
                        "token_count": {
                            "prompt": response.usage.prompt_tokens,
                            "completion": response.usage.completion_tokens,
                            "total": response.usage.total_tokens
                        },
                        "rate_limits": {
                            "minute": {
                                "remaining": 3 - rate_data["minute_count"],
                                "reset": rate_data["minute_reset"]
                            },
                            "day": {
                                "remaining": 30 - rate_data["day_count"],
                                "reset": rate_data["day_reset"]
                            }
                        }
                    }
                    
                    return jsonify(response_obj), 201
                    
                except Exception as db_err:
                    app.logger.error(f"Database error: {str(db_err)}")
                    # If DB operation fails, still return the generated content
                    return jsonify({
                        "content": html_content,
                        "title": title,
                        "warning": "Document was generated but could not be saved to database"
                    }), 200
                    
            except openai.APITimeoutError:
                app.logger.error("OpenAI API timeout")
                return jsonify({
                    "error": "AI service timeout", 
                    "details": "The request took too long to process. Please try again with fewer or smaller reference materials."
                }), 504
                
            except openai.RateLimitError:
                app.logger.error("OpenAI API rate limit exceeded")
                return jsonify({
                    "error": "AI service unavailable", 
                    "details": "The AI service is currently experiencing high demand. Please try again in a few minutes."
                }), 503
                
            except openai.APIError as api_err:
                app.logger.error(f"OpenAI API error: {str(api_err)}")
                return jsonify({
                    "error": "AI service error", 
                    "details": str(api_err)
                }), 503
                
        except Exception as e:
            app.logger.error(f"Error in document generation: {str(e)}")
            return jsonify({"error": "Document generation failed", "details": str(e)}), 500
            
    except Exception as e:
        app.logger.error(f"Unexpected error in generate_document: {str(e)}")
        return jsonify({"error": "Server error", "details": str(e)}), 500

@app.route('/api/ai/improve-document', methods=['POST'])
def improve_document():
    """
    Endpoint to improve a document using AI suggestions.
    Takes a document ID and content, returns improved content.
    """
    # Validate OpenAI API key presence
    if not openai.api_key:
        return jsonify({"error": "Server configuration error: OpenAI API key not found"}), 500
    
    try:
        # Validate user authentication
        user_id = request.headers.get('user-id')
        if not user_id:
            return jsonify({"error": "Authentication required", "details": "User ID header is missing"}), 401
        
        # Parse and validate request body
        if not request.json:
            return jsonify({"error": "Invalid request", "details": "Request body must be JSON"}), 400
            
        data = request.json
        
        # Validate required fields
        required_fields = ['document_id', 'content', 'improvement_type']
        missing_fields = [field for field in required_fields if not data.get(field)]
        
        if missing_fields:
            return jsonify({
                "error": "Missing required fields", 
                "details": f"The following fields are required: {', '.join(missing_fields)}"
            }), 400
        
        # Get document details
        document_id = data.get('document_id')
        content = data.get('content')
        improvement_type = data.get('improvement_type', 'grammar')
        
        # Validate document ownership
        try:
            document_response = db.get_document(document_id, user_id)
            if not document_response or not document_response.data:
                return jsonify({"error": "Document not found or access denied"}), 404
        except Exception as db_err:
            app.logger.error(f"Database error when validating document: {str(db_err)}")
            return jsonify({"error": "Database error", "details": str(db_err)}), 500
        
        # Determine improvement instructions based on type
        system_prompt = "You are an expert editor helping improve a document."
        
        if improvement_type == 'grammar':
            system_prompt += " Focus on correcting grammar, spelling, and punctuation while preserving the original meaning and style."
            instruction = "Improve the grammar, spelling, and punctuation of this text. Keep the same content and meaning."
        elif improvement_type == 'clarity':
            system_prompt += " Focus on improving clarity and readability while maintaining the original message."
            instruction = "Improve the clarity and readability of this text. Make it more concise and easier to understand."
        elif improvement_type == 'diplomacy':
            system_prompt += " Focus on making the language more formal and diplomatic, suitable for international relations."
            instruction = "Make this text more diplomatic and formal in tone, appropriate for a Model UN context."
        else:
            system_prompt += " Improve the overall quality of the document while preserving its purpose."
            instruction = "Improve this document's overall quality while preserving its main points and structure."
        
        # Make the OpenAI API call
        try:
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",  # Use a cost-effective model for editing
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"{instruction}\n\nOriginal text:\n{content}"}
                ],
                temperature=0.3,  # Lower temperature for more consistent editing
                max_tokens=2048,
                timeout=30
            )
            
            # Validate response
            if not response or not response.choices or len(response.choices) == 0:
                return jsonify({"error": "Empty response from AI model"}), 500
                
            # Extract the improved text
            improved_text = response.choices[0].message.content
            
            # Update the document in the database
            try:
                document_data = {
                    "content": improved_text,
                    "updated_at": datetime.now().isoformat()
                }
                
                db.update_document(document_id, user_id, document_data)
                
                # Return success response
                return jsonify({
                    "document_id": document_id,
                    "improved_content": improved_text,
                    "improvement_type": improvement_type
                }), 200
                
            except Exception as db_err:
                app.logger.error(f"Database error when updating document: {str(db_err)}")
                # If DB operation fails, still return the improved content
                return jsonify({
                    "improved_content": improved_text,
                    "warning": "Content was improved but could not be saved to database"
                }), 200
                
        except Exception as openai_err:
            app.logger.error(f"OpenAI API error: {str(openai_err)}")
            return jsonify({"error": f"AI service error: {str(openai_err)}"}), 503
            
    except Exception as e:
        app.logger.error(f"Unexpected error in improve_document: {str(e)}")
        return jsonify({"error": "Server error", "details": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True) 