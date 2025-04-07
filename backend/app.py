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

# Register background guide blueprint
try:
    from background_guide.api import bg_blueprint
    app.register_blueprint(bg_blueprint, url_prefix='/api/background-guide')
    print("Background guide blueprint registered successfully")
except ImportError as e:
    print(f"Could not register background guide blueprint: {e}")

# Register mind map blueprint
try:
    from mind_map.api import mind_map_blueprint
    app.register_blueprint(mind_map_blueprint, url_prefix='/api/mind-map')
    print("Mind map blueprint registered successfully")
except ImportError as e:
    print(f"Could not register mind map blueprint: {e}")

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
            # Prepare the system prompt based on document type
            if document_type == 'position_paper':
                system_prompt = f"""You are an expert Model UN advisor helping create a position paper.

{delegate_profile}

WRITING STYLE GUIDELINES:
{writing_style_guidelines}

FORMATTING GUIDELINES:
{formatting_guidelines if formatting_guidelines else "Follow standard Model UN position paper format."}

Create a formal, well-researched position paper that:
1. States {country}'s position on {topic}
2. References information from the background guide AND recent developments
3. Includes specific policy proposals aligned with {country}'s actual foreign policy
4. Uses proper citations for factual claims
5. Is structured with clear introduction, body, and conclusion
6. Is approximately 1000-1500 words

Use formal diplomatic language. Incorporate relevant details from the background guide and web research.
Format the document with proper HTML tags for headings, paragraphs, and lists."""
            
            elif document_type == 'resolution':
                system_prompt = f"""You are an expert Model UN advisor helping create a resolution paper.

{delegate_profile}

WRITING STYLE GUIDELINES:
{writing_style_guidelines}

FORMATTING GUIDELINES:
{formatting_guidelines if formatting_guidelines else "Follow standard Model UN resolution format with preambulatory and operative clauses."}

Create a formal UN-style resolution that:
1. Addresses {topic} from {country}'s perspective
2. Uses proper preambulatory clauses that reference existing UN actions
3. Includes specific, actionable operative clauses
4. Follows proper resolution formatting and numbering
5. Is realistic and aligned with {country}'s actual foreign policy
6. Uses formal diplomatic language throughout

Begin preambulatory clauses with phrases like "Recalling," "Noting," etc.
Begin operative clauses with action verbs like "Requests," "Decides," etc.
Format with proper indentation and numbering following UN standards."""
            
            else:  # speech
                system_prompt = f"""You are an expert Model UN advisor helping create a formal speech.

{delegate_profile}

WRITING STYLE GUIDELINES:
{writing_style_guidelines}

FORMATTING GUIDELINES:
{formatting_guidelines if formatting_guidelines else "Create a speech suitable for 3-4 minute delivery (approximately 500-700 words)."}

Create a well-structured, engaging speech that:
1. Begins with appropriate committee greeting
2. Clearly states {country}'s position on {topic}
3. Provides 2-3 key arguments supported by evidence
4. References recent developments and relevant UN actions
5. Ends with a call to action and appropriate closing
6. Uses proper diplomatic language appropriate for {committee}
7. Is concise and suitable for oral delivery

Format the speech with appropriate paragraph breaks and emphasis on key points."""
            
            # Combine reference materials if any
            background_text = "\n\n".join(reference_texts) if reference_texts else ""
            if background_text and len(background_text) > 6000:
                background_text = background_text[:6000] + "... [text truncated for length]"
            
            # Prepare mind map content if available
            mind_map_content = ""
            if mind_map:
                try:
                    # Convert mind map to a structured text format
                    mind_map_content = f"""
                    TOPIC ANALYSIS: {mind_map.get('topic', topic)}
                    
                    KEY ISSUES:
                    {', '.join(mind_map.get('key_issues', []))}
                    
                    HISTORICAL CONTEXT:
                    {', '.join(mind_map.get('historical_context', []))}
                    
                    POTENTIAL SOLUTIONS:
                    {', '.join(mind_map.get('potential_solutions', []))}
                    
                    RELEVANT COUNTRIES:
                    {', '.join(mind_map.get('countries_mentioned', []))}
                    
                    SUBTOPICS:
                    """
                    
                    for subtopic in mind_map.get('subtopics', []):
                        mind_map_content += f"\n- {subtopic.get('name', '')}: {', '.join(subtopic.get('key_points', []))}"
                        
                except Exception:
                    mind_map_content = "Topic analysis available but could not be formatted."
            
            # Construct the user prompt with all available information
            user_prompt = f"""Generate a {document_type.replace('_', ' ')} with the following details:

COMMITTEE: {committee}
COUNTRY: {country}
TOPIC: {topic}

BACKGROUND GUIDE SUMMARY:
{background_guide_text[:2000] if background_guide_text else "No background guide provided."}

TOPIC ANALYSIS:
{mind_map_content if mind_map_content else "No detailed topic analysis available."}

WEB SEARCH INFORMATION:
{search_results_combined}

ADDITIONAL CONTEXT:
{additional_context}

Create a complete, ready-to-use document that represents {country}'s actual positions and follows proper formatting."""
            
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

# User onboarding routes
@app.route('/api/onboarding/status', methods=['GET'])
def get_onboarding_status():
    """Check if the user has completed onboarding"""
    try:
        user_id = request.headers.get('user-id')
        if not user_id:
            return jsonify({"error": "User ID required"}), 400
        
        is_onboarded = db.check_user_onboarding_status(user_id)
        return jsonify({"is_onboarded": is_onboarded}), 200
    except Exception as e:
        app.logger.error(f"Error checking onboarding status: {str(e)}")
        return jsonify({"error": str(e)}), 400

@app.route('/api/onboarding/writing-profile', methods=['POST'])
def create_writing_profile():
    """Process and create a writing style profile during onboarding"""
    if not openai.api_key:
        return jsonify({"error": "Server configuration error: OpenAI API key not found"}), 500
    
    try:
        user_id = request.headers.get('user-id')
        if not user_id:
            return jsonify({"error": "User ID required"}), 400
        
        # Parse request data
        data = request.get_json()
        
        writing_samples = data.get('writing_samples', '')
        preferred_topics = data.get('preferred_topics', [])
        preferred_countries = data.get('preferred_countries', [])
        delegate_style = data.get('delegate_style', '')
        past_papers = data.get('past_papers', '')
        past_speeches = data.get('past_speeches', '')
        past_resolutions = data.get('past_resolutions', '')
        
        # Combine all text for analysis if available
        all_text_samples = []
        if writing_samples:
            all_text_samples.append(writing_samples)
        if delegate_style:
            all_text_samples.append(delegate_style)
        if past_papers:
            all_text_samples.append(past_papers)
        if past_speeches:
            all_text_samples.append(past_speeches)
        if past_resolutions:
            all_text_samples.append(past_resolutions)
            
        combined_text = "\n\n".join(all_text_samples)
        
        # Don't process if samples are too short
        if len(combined_text) < 50:
            # Store minimal profile without AI processing
            profile_data = {
                "writing_style": "default",
                "tone": "formal",
                "sentence_structure": "balanced",
                "complexity_level": "intermediate",
                "formality_level": "formal",
                "creativity_level": "balanced",
                "delegate_style": delegate_style,
                "research_depth": "moderate",
                "argument_structure": "standard",
                "sample_document_content": writing_samples[:100] if writing_samples else "",
                "parsed_style_data": {},
                "delegate_profile_created": False,
                "consolidated_delegate_profile": ""
            }
            
            db.create_user_writing_profile(user_id, profile_data)
            
            # Update user stats with preferences
            db.update_user_stats(user_id, {
                "preferred_topics": preferred_topics,
                "preferred_countries": preferred_countries
            })
            
            return jsonify({
                "message": "Basic writing profile created. AI analysis skipped due to limited sample text.",
                "profile": profile_data
            }), 201
        
        # Process with AI if samples are long enough
        try:
            system_prompt = """You are an expert writing analyst. Analyze the provided writing sample(s) 
            and extract key stylistic elements. Return a JSON object with the following fields:
            - writing_style: a brief description of the overall writing style
            - tone: the tone of the writing (formal, casual, etc.)
            - sentence_structure: description of sentence complexity and variety
            - complexity_level: one of [basic, intermediate, advanced]
            - formality_level: one of [casual, neutral, formal, very formal]
            - creativity_level: one of [factual, balanced, creative]
            - research_depth: one of [minimal, moderate, thorough, extensive]
            - argument_structure: description of how arguments are typically structured
            - key_patterns: array of notable writing patterns
            - delegate_style_analysis: analysis of the delegate's approach in MUN contexts
            
            Ensure the analysis is objective and focuses on STYLE, not content."""
            
            user_prompt = f"""Analyze the following writing sample(s) for stylistic elements only:

{combined_text}

Remember to return ONLY a JSON object with the specified fields."""
            
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=600,
                response_format={"type": "json_object"}
            )
            
            # Extract the analysis from the API response
            if not response or not response.choices or len(response.choices) == 0:
                raise Exception("Empty response from AI model")
            
            analysis_text = response.choices[0].message.content
            
            # Parse the JSON response
            import json
            try:
                analysis = json.loads(analysis_text)
            except json.JSONDecodeError:
                # If parsing fails, create a default analysis
                analysis = {
                    "writing_style": "default",
                    "tone": "formal",
                    "sentence_structure": "balanced",
                    "complexity_level": "intermediate",
                    "formality_level": "formal", 
                    "creativity_level": "balanced",
                    "research_depth": "moderate",
                    "argument_structure": "standard",
                    "key_patterns": [],
                    "delegate_style_analysis": "Formal diplomatic approach"
                }
            
            # Flag to check if we should create a consolidated profile
            create_consolidated_profile = len(combined_text) >= 200
            consolidated_profile = ""
            
            # Only create the consolidated profile if we have enough text
            if create_consolidated_profile:
                try:
                    consolidation_prompt = f"""Create a concise but comprehensive profile of this Model UN delegate based on the analyzed writing samples.
                    The profile should capture their writing style, delegate approach, and key characteristics in a structured format that can
                    be used as a reference for generating personalized documents.
                    
                    Data points to consider:
                    - Writing style: {analysis.get("writing_style", "formal")}
                    - Tone: {analysis.get("tone", "formal diplomatic")}
                    - Sentence structure: {analysis.get("sentence_structure", "balanced")}
                    - Complexity level: {analysis.get("complexity_level", "intermediate")}
                    - Formality level: {analysis.get("formality_level", "formal")}
                    - Creativity level: {analysis.get("creativity_level", "balanced")}
                    - Research depth: {analysis.get("research_depth", "moderate")}
                    - Argument structure: {analysis.get("argument_structure", "standard")}
                    - Delegate style: {delegate_style}
                    - Preferred topics: {", ".join(preferred_topics) if preferred_topics else "None specified"}
                    - Preferred countries: {", ".join(preferred_countries) if preferred_countries else "None specified"}
                    
                    Format this as a comprehensive profile that captures their essence as a delegate in about 300-500 words.
                    The profile should be structured to be easily referenced when generating documents."""
                    
                    profile_response = openai.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": "You are a specialized Model UN coach who creates delegate profiles."},
                            {"role": "user", "content": consolidation_prompt}
                        ],
                        temperature=0.3,
                        max_tokens=800
                    )
                    
                    consolidated_profile = profile_response.choices[0].message.content
                except Exception as profile_err:
                    app.logger.error(f"Error creating consolidated profile: {str(profile_err)}")
                    consolidated_profile = "Error creating consolidated profile."
            
            # Store the writing profile
            profile_data = {
                "writing_style": analysis.get("writing_style", "default"),
                "tone": analysis.get("tone", "formal"),
                "sentence_structure": analysis.get("sentence_structure", "balanced"),
                "complexity_level": analysis.get("complexity_level", "intermediate"),
                "formality_level": analysis.get("formality_level", "formal"),
                "creativity_level": analysis.get("creativity_level", "balanced"),
                "research_depth": analysis.get("research_depth", "moderate"),
                "argument_structure": analysis.get("argument_structure", "standard"),
                "delegate_style": delegate_style,
                "sample_document_content": combined_text[:1000],  # Store a sample, limited to 1000 chars
                "parsed_style_data": analysis,
                "delegate_profile_created": create_consolidated_profile,
                "consolidated_delegate_profile": consolidated_profile
            }
            
            db.create_user_writing_profile(user_id, profile_data)
            
            # Update user stats with preferences
            db.update_user_stats(user_id, {
                "preferred_topics": preferred_topics,
                "preferred_countries": preferred_countries
            })
            
            return jsonify({
                "message": "Writing profile created successfully",
                "profile": profile_data
            }), 201
            
        except Exception as ai_err:
            app.logger.error(f"Error analyzing writing style: {str(ai_err)}")
            # Create a default profile if AI analysis fails
            profile_data = {
                "writing_style": "default",
                "tone": "formal",
                "sentence_structure": "balanced",
                "complexity_level": "intermediate",
                "formality_level": "formal",
                "creativity_level": "balanced",
                "research_depth": "moderate",
                "argument_structure": "standard",
                "delegate_style": delegate_style,
                "sample_document_content": combined_text[:200] if combined_text else "",
                "parsed_style_data": {
                    "error": "AI analysis failed, using default values"
                },
                "delegate_profile_created": False,
                "consolidated_delegate_profile": ""
            }
            
            db.create_user_writing_profile(user_id, profile_data)
            
            # Update user stats with preferences
            db.update_user_stats(user_id, {
                "preferred_topics": preferred_topics,
                "preferred_countries": preferred_countries
            })
            
            return jsonify({
                "message": "Basic writing profile created. AI analysis failed.",
                "profile": profile_data
            }), 201
            
    except Exception as e:
        app.logger.error(f"Error creating writing profile: {str(e)}")
        return jsonify({"error": str(e)}), 400

@app.route('/api/onboarding/complete', methods=['POST'])
def complete_onboarding():
    """Mark user onboarding as complete"""
    try:
        user_id = request.headers.get('user-id')
        if not user_id:
            return jsonify({"error": "User ID required"}), 400
        
        db.complete_user_onboarding(user_id)
        return jsonify({"message": "Onboarding completed successfully"}), 200
    except Exception as e:
        app.logger.error(f"Error completing onboarding: {str(e)}")
        return jsonify({"error": str(e)}), 400

# Document creation session routes
@app.route('/api/document-sessions', methods=['POST'])
def create_document_session():
    """Create a new document creation session"""
    try:
        user_id = request.headers.get('user-id')
        if not user_id:
            return jsonify({"error": "User ID required"}), 400
        
        data = request.get_json()
        document_type = data.get('document_type')
        
        if not document_type:
            return jsonify({"error": "Document type is required"}), 400
        
        # Create the session
        session_data = {
            "document_type": document_type,
            "status": "in_progress"
        }
        
        response = db.create_document_creation_session(user_id, session_data)
        
        return jsonify({
            "message": "Document creation session started",
            "session": response.data[0] if response.data else None
        }), 201
    except Exception as e:
        app.logger.error(f"Error creating document session: {str(e)}")
        return jsonify({"error": str(e)}), 400

@app.route('/api/document-sessions/<int:session_id>', methods=['GET'])
def get_document_session(session_id):
    """Get a specific document creation session"""
    try:
        user_id = request.headers.get('user-id')
        if not user_id:
            return jsonify({"error": "User ID required"}), 400
        
        response = db.get_document_creation_session(session_id, user_id)
        
        if not response.data:
            return jsonify({"error": "Session not found"}), 404
        
        return jsonify(response.data), 200
    except Exception as e:
        app.logger.error(f"Error getting document session: {str(e)}")
        return jsonify({"error": str(e)}), 400

@app.route('/api/document-sessions/<int:session_id>', methods=['PUT'])
def update_document_session(session_id):
    """Update a document creation session"""
    try:
        user_id = request.headers.get('user-id')
        if not user_id:
            return jsonify({"error": "User ID required"}), 400
        
        data = request.get_json()
        
        response = db.update_document_creation_session(session_id, user_id, data)
        
        return jsonify({
            "message": "Session updated successfully",
            "session": response.data[0] if response.data else None
        }), 200
    except Exception as e:
        app.logger.error(f"Error updating document session: {str(e)}")
        return jsonify({"error": str(e)}), 400

@app.route('/api/document-sessions/<int:session_id>/upload-background', methods=['POST'])
def upload_background_guide(session_id):
    """Upload and process a background guide for a document session"""
    if not openai.api_key:
        return jsonify({"error": "Server configuration error: OpenAI API key not found"}), 500
    
    try:
        user_id = request.headers.get('user-id')
        if not user_id:
            return jsonify({"error": "User ID required"}), 400
        
        # Verify session exists
        session_response = db.get_document_creation_session(session_id, user_id)
        if not session_response.data:
            return jsonify({"error": "Session not found"}), 404
        
        # Get the file
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        # Check file size (5MB max)
        file_data = file.read()
        file.seek(0)  # Reset file pointer after reading
        
        if len(file_data) > 5 * 1024 * 1024:
            return jsonify({"error": "File too large (max 5MB)"}), 400
        
        # Parse the file to extract text
        try:
            from utils.document_parser import extract_text_from_file
            extracted_text = extract_text_from_file(file_data, file.content_type)
            
            if not extracted_text or len(extracted_text) < 100:
                return jsonify({"error": "Could not extract sufficient text from the file"}), 400
            
            # Extract formatting guidelines if they exist
            try:
                # Look for formatting guidelines in the first 5000 characters
                sample_text = extracted_text[:5000].lower()
                
                system_prompt = """You are a document analyst specialized in Model UN background guides.
                Analyze the beginning of the provided background guide and extract ONLY the formatting guidelines for position papers,
                if they exist. Return ONLY the exact formatting guidelines as a string. If no specific formatting guidelines
                are found, return 'No specific formatting guidelines found.'"""
                
                response = openai.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Extract position paper formatting guidelines from this background guide:\n\n{sample_text}"}
                    ],
                    temperature=0.3,
                    max_tokens=300
                )
                
                formatting_guidelines = response.choices[0].message.content
                
                # If no guidelines found, it will contain the "No specific" text
                
            except Exception as format_err:
                app.logger.error(f"Error extracting formatting guidelines: {str(format_err)}")
                formatting_guidelines = "No specific formatting guidelines found."
            
            # Update the session with the extracted text
            update_data = {
                "background_guide_text": extracted_text,
                "extracted_formatting": formatting_guidelines if "No specific" not in formatting_guidelines else None
            }
            
            db.update_document_creation_session(session_id, user_id, update_data)
            
            return jsonify({
                "message": "Background guide processed successfully",
                "text_length": len(extracted_text),
                "has_formatting_guidelines": "No specific" not in formatting_guidelines,
                "formatting_guidelines": formatting_guidelines if "No specific" not in formatting_guidelines else None
            }), 200
            
        except Exception as parse_err:
            app.logger.error(f"Error parsing document: {str(parse_err)}")
            return jsonify({"error": f"Failed to parse document: {str(parse_err)}"}), 400
        
    except Exception as e:
        app.logger.error(f"Error uploading background guide: {str(e)}")
        return jsonify({"error": str(e)}), 400

@app.route('/api/document-sessions/<int:session_id>/analyze-topic', methods=['POST'])
def analyze_topic(session_id):
    """Analyze the specified topic and create a mind map from the background guide"""
    if not openai.api_key:
        return jsonify({"error": "Server configuration error: OpenAI API key not found"}), 500
    
    try:
        user_id = request.headers.get('user-id')
        if not user_id:
            return jsonify({"error": "User ID required"}), 400
        
        # Get the session
        session_response = db.get_document_creation_session(session_id, user_id)
        if not session_response.data:
            return jsonify({"error": "Session not found"}), 404
        
        session = session_response.data
        
        # Get the topic from request
        data = request.get_json()
        topic = data.get('topic')
        
        if not topic:
            return jsonify({"error": "Topic is required"}), 400
        
        # Update the session with the topic
        db.update_document_creation_session(session_id, user_id, {"topic": topic})
        
        # Check if we have a background guide to analyze
        if not session.get('background_guide_text'):
            return jsonify({
                "message": "No background guide available for analysis", 
                "mind_map": None
            }), 200
        
        # Extract relevant portions of the background guide for the topic
        background_text = session.get('background_guide_text')
        
        try:
            # Create a mind map of the topic from the background guide
            system_prompt = """You are an expert at analyzing Model UN background guides. 
            Create a detailed mind map in JSON format for the specified topic based on the provided background guide.
            Focus ONLY on the parts of the guide that are relevant to the specified topic.
            
            Return a JSON object with the following structure:
            {
                "topic": "The main topic",
                "subtopics": [
                    {
                        "name": "Subtopic name",
                        "key_points": ["Point 1", "Point 2"],
                        "relevant_actors": ["Actor 1", "Actor 2"]
                    }
                ],
                "key_issues": ["Issue 1", "Issue 2"],
                "historical_context": ["Context 1", "Context 2"],
                "potential_solutions": ["Solution 1", "Solution 2"],
                "countries_mentioned": ["Country 1", "Country 2"]
            }"""
            
            user_prompt = f"""Create a mind map for the topic "{topic}" based on this background guide:

{background_text[:8000]}  # Limit to 8000 characters to stay within token limits

Return ONLY the JSON mind map without additional explanations."""
            
            response = openai.chat.completions.create(
                model="gpt-4o-mini",  # Use a more capable model for complex analysis
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=1000,
                response_format={"type": "json_object"}
            )
            
            # Extract the mind map JSON
            mind_map_text = response.choices[0].message.content
            
            # Parse the JSON
            import json
            try:
                mind_map = json.loads(mind_map_text)
            except json.JSONDecodeError:
                # If parsing fails, create a simple mind map
                mind_map = {
                    "topic": topic,
                    "subtopics": [],
                    "key_issues": [],
                    "historical_context": [],
                    "potential_solutions": [],
                    "countries_mentioned": []
                }
            
            # Update the session with the mind map
            db.update_document_creation_session(session_id, user_id, {"mind_map": mind_map})
            
            return jsonify({
                "message": "Topic analyzed successfully",
                "mind_map": mind_map
            }), 200
            
        except Exception as analyze_err:
            app.logger.error(f"Error analyzing topic: {str(analyze_err)}")
            return jsonify({"error": f"Failed to analyze topic: {str(analyze_err)}"}), 400
        
    except Exception as e:
        app.logger.error(f"Error analyzing topic: {str(e)}")
        return jsonify({"error": str(e)}), 400

@app.route('/api/document-sessions/<int:session_id>/generate-document', methods=['POST'])
def generate_document_from_session(session_id):
    """Generate a document based on the session data with web search augmentation"""
    if not openai.api_key:
        return jsonify({"error": "Server configuration error: OpenAI API key not found"}), 500
    
    try:
        user_id = request.headers.get('user-id')
        if not user_id:
            return jsonify({"error": "User ID required"}), 400
        
        # Get the session
        session_response = db.get_document_creation_session(session_id, user_id)
        if not session_response.data:
            return jsonify({"error": "Session not found"}), 404
        
        session = session_response.data
        
        # Validate required fields
        required_fields = ['document_type', 'committee', 'country', 'topic']
        missing_fields = [field for field in required_fields if not session.get(field)]
        
        if missing_fields:
            return jsonify({
                "error": "Missing required fields", 
                "details": f"The following fields are required: {', '.join(missing_fields)}"
            }), 400
        
        # Mark session as generating
        db.update_document_creation_session(session_id, user_id, {"status": "generating"})
        
        # Get user's writing profile
        profile_response = db.get_user_writing_profile(user_id)
        writing_profile = profile_response.data if profile_response.data else {}
        
        # Prepare data for generation
        document_type = session.get('document_type')
        committee = session.get('committee')
        country = session.get('country')
        topic = session.get('topic')
        mind_map = session.get('mind_map', {})
        background_guide_text = session.get('background_guide_text', '')
        formatting_guidelines = session.get('extracted_formatting')
        
        # Get additional context from the request
        data = request.get_json()
        additional_context = data.get('additional_context', '')
        
        try:
            # First call: Look up additional information on the web about the topic and country position
            web_search_system_prompt = """You are a Model UN research assistant. 
            Based on the topic and country provided, what are the 3-5 most important web searches we should make to find:
            1. Recent developments on this topic (last 2 years)
            2. The country's actual position and policies on this topic
            3. Relevant UN resolutions or international agreements
            
            Return ONLY a JSON array of search queries, with no additional text."""
            
            web_search_prompt = f"""Create web search queries for researching:
            
            TOPIC: {topic}
            COUNTRY: {country}
            COMMITTEE: {committee}
            
            Return ONLY the JSON array of search queries."""
            
            search_response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": web_search_system_prompt},
                    {"role": "user", "content": web_search_prompt}
                ],
                temperature=0.5,
                max_tokens=300,
                response_format={"type": "json_object"}
            )
            
            import json
            try:
                search_queries = json.loads(search_response.choices[0].message.content)
                # If returned object is not a list but has a "queries" field
                if isinstance(search_queries, dict) and "queries" in search_queries:
                    search_queries = search_queries["queries"]
                # If it's still not a list, convert to list
                if not isinstance(search_queries, list):
                    search_queries = [str(search_queries)]
            except (json.JSONDecodeError, TypeError):
                # Fallback if JSON parsing fails
                search_queries = [f"{country} position on {topic}", f"recent developments {topic}", f"UN {committee} {topic}"]
            
            # Simulate web search results (in a real app, this would be an actual search API call)
            # This is a placeholder for demonstration
            search_results_combined = f"""
            Web search results for: {', '.join(search_queries[:3])}
            
            SIMULATED SEARCH RESULTS: In a production environment, this would contain actual search results
            from a search API or web scraping. For this demonstration, we're simulating relevant web content.
            
            Recent information about {topic} includes several key developments in the past year.
            {country} has generally supported international cooperation on this issue through various UN forums.
            
            The most recent UN resolution related to this topic was passed in the General Assembly last year,
            calling for increased cooperation among member states.
            """
            
            # Get additional data like delegate profile if available
            delegate_profile = ""
            writing_style_guidelines = "Use formal diplomatic language appropriate for Model UN."
            
            if writing_profile:
                # Check if we have a consolidated delegate profile
                if writing_profile.get('delegate_profile_created', False) and writing_profile.get('consolidated_delegate_profile'):
                    app.logger.info(f"Using consolidated delegate profile for user {user_id}")
                    delegate_profile = f"""
                    DELEGATE PROFILE:
                    {writing_profile.get('consolidated_delegate_profile')}
                    """
                
                # Create writing style guidelines from individual components
                writing_style_guidelines = f"""
                Writing style: {writing_profile.get('writing_style', 'formal')}
                Tone: {writing_profile.get('tone', 'formal diplomatic')}
                Sentence structure: {writing_profile.get('sentence_structure', 'varied')}
                Complexity level: {writing_profile.get('complexity_level', 'intermediate')}
                Formality level: {writing_profile.get('formality_level', 'formal')}
                Creativity level: {writing_profile.get('creativity_level', 'balanced')}
                Research depth: {writing_profile.get('research_depth', 'moderate')}
                Argument structure: {writing_profile.get('argument_structure', 'standard')}
                """
            
            # Prepare mind map content if available
            mind_map_content = ""
            if mind_map:
                try:
                    # Convert mind map to a structured text format
                    mind_map_content = f"""
                    TOPIC ANALYSIS: {mind_map.get('topic', topic)}
                    
                    KEY ISSUES:
                    {', '.join(mind_map.get('key_issues', []))}
                    
                    HISTORICAL CONTEXT:
                    {', '.join(mind_map.get('historical_context', []))}
                    
                    POTENTIAL SOLUTIONS:
                    {', '.join(mind_map.get('potential_solutions', []))}
                    
                    RELEVANT COUNTRIES:
                    {', '.join(mind_map.get('countries_mentioned', []))}
                    
                    SUBTOPICS:
                    """
                    
                    for subtopic in mind_map.get('subtopics', []):
                        mind_map_content += f"\n- {subtopic.get('name', '')}: {', '.join(subtopic.get('key_points', []))}"
                        
                except Exception:
                    mind_map_content = "Topic analysis available but could not be formatted."
            
            # Construct the user prompt with all available information
            user_prompt = f"""Generate a {document_type.replace('_', ' ')} with the following details:

COMMITTEE: {committee}
COUNTRY: {country}
TOPIC: {topic}

BACKGROUND GUIDE SUMMARY:
{background_guide_text[:2000] if background_guide_text else "No background guide provided."}

TOPIC ANALYSIS:
{mind_map_content if mind_map_content else "No detailed topic analysis available."}

WEB SEARCH INFORMATION:
{search_results_combined}

ADDITIONAL CONTEXT:
{additional_context}

Create a complete, ready-to-use document that represents {country}'s actual positions and follows proper formatting."""
            
            # Make the document generation API call
            response = openai.chat.completions.create(
                model="gpt-4o-mini",  # Use a more capable model for final document
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=2500  # Allow for longer output
            )
            
            # Extract the generated text
            generated_text = response.choices[0].message.content
            
            # Add wrapper div for styling
            html_content = f"<div class='{document_type.replace('_', '-')}'>{generated_text}</div>"
            
            # Create a proper title
            if document_type == 'position_paper':
                title = f"Position Paper: {country} on {topic}"
            elif document_type == 'resolution':
                title = f"Resolution: {topic} ({country})"
            else:  # speech
                title = f"Speech: {country} on {topic}"
            
            # Create document in database
            document_data = {
                "title": title,
                "type": document_type.replace('_', ' ').title(),
                "committee": committee,
                "conference": "Generated from session",
                "content": html_content,
                "source_urls": search_queries,  # Store the search queries used
                "background_guide_text": background_guide_text[:5000] if background_guide_text else None,
                "progress": 100,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            document_response = db.create_document(user_id, document_data)
            
            # Update the session
            db.update_document_creation_session(session_id, user_id, {
                "status": "completed",
                "session_data": {
                    "document_id": document_response.data[0]['id'] if document_response.data else None,
                    "generated_at": datetime.now().isoformat()
                }
            })
            
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
            
            # Return success response
            return jsonify({
                "message": "Document generated successfully",
                "document_id": document_response.data[0]['id'] if document_response.data else None,
                "title": title,
                "content": html_content
            }), 201
            
        except Exception as gen_err:
            app.logger.error(f"Error generating document: {str(gen_err)}")
            # Update session status to failed
            db.update_document_creation_session(session_id, user_id, {"status": "failed"})
            return jsonify({"error": f"Document generation failed: {str(gen_err)}"}), 500
            
    except Exception as e:
        app.logger.error(f"Error in document generation endpoint: {str(e)}")
        return jsonify({"error": str(e)}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True) 