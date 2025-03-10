"""
Authentication routes for user authentication and authorization.
"""
from flask import request, jsonify, current_app
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt_identity,
    jwt_required,
)
from app.auth import auth_bp
from app.core.utils import supabase_request, generate_uuid
from app.core.errors import (
    BadRequestError,
    UnauthorizedError,
    ValidationFailedError,
    ConflictError,
)
from app.core.schemas import ProfileSchema
from marshmallow import ValidationError


@auth_bp.route("/register", methods=["POST"])
def register():
    """
    Register a new user.
    
    Request body:
        email (str): User's email
        password (str): User's password
        username (str): User's username
        
    Returns:
        JSON: User data and tokens
    """
    data = request.get_json()
    
    if not data:
        raise BadRequestError("No input data provided")
    
    # Validate required fields
    required_fields = ["email", "password", "username"]
    for field in required_fields:
        if field not in data:
            raise ValidationFailedError(f"Missing required field: {field}")
    
    email = data.get("email")
    password = data.get("password")
    username = data.get("username")
    
    # Validate username
    try:
        ProfileSchema().validate({"username": username})
    except ValidationError as e:
        raise ValidationFailedError(str(e))
    
    # Check if username already exists
    try:
        existing_user = supabase_request(
            method="GET",
            endpoint=f"/rest/v1/profiles?username=eq.{username}",
        )
        
        if existing_user and len(existing_user) > 0:
            raise ConflictError("Username already exists")
    except Exception as e:
        if isinstance(e, ConflictError):
            raise
        current_app.logger.error(f"Error checking username: {str(e)}")
    
    # Register user with Supabase Auth
    try:
        auth_response = supabase_request(
            method="POST",
            endpoint="/auth/v1/signup",
            data={
                "email": email,
                "password": password,
            },
        )
        
        if "error" in auth_response:
            raise BadRequestError(auth_response.get("error_description", "Registration failed"))
        
        user_id = auth_response.get("user", {}).get("id")
        
        if not user_id:
            raise BadRequestError("Failed to create user")
        
        # Create profile in Supabase
        profile_data = {
            "id": user_id,
            "username": username,
            "created_at": auth_response.get("user", {}).get("created_at"),
            "updated_at": auth_response.get("user", {}).get("created_at"),
        }
        
        profile_response = supabase_request(
            method="POST",
            endpoint="/rest/v1/profiles",
            data=profile_data,
        )
        
        # Generate tokens
        access_token = create_access_token(identity=user_id)
        refresh_token = create_refresh_token(identity=user_id)
        
        return jsonify({
            "message": "User registered successfully",
            "user": {
                "id": user_id,
                "email": email,
                "username": username,
            },
            "tokens": {
                "access_token": access_token,
                "refresh_token": refresh_token,
            }
        }), 201
        
    except Exception as e:
        if isinstance(e, (BadRequestError, ValidationFailedError, ConflictError)):
            raise
        current_app.logger.error(f"Registration error: {str(e)}")
        raise BadRequestError("Registration failed")


@auth_bp.route("/login", methods=["POST"])
def login():
    """
    Login a user.
    
    Request body:
        email (str): User's email
        password (str): User's password
        
    Returns:
        JSON: User data and tokens
    """
    data = request.get_json()
    
    if not data:
        raise BadRequestError("No input data provided")
    
    # Validate required fields
    required_fields = ["email", "password"]
    for field in required_fields:
        if field not in data:
            raise ValidationFailedError(f"Missing required field: {field}")
    
    email = data.get("email")
    password = data.get("password")
    
    try:
        # Login with Supabase Auth
        auth_response = supabase_request(
            method="POST",
            endpoint="/auth/v1/token",
            data={
                "email": email,
                "password": password,
                "grant_type": "password",
            },
        )
        
        if "error" in auth_response:
            raise UnauthorizedError(auth_response.get("error_description", "Invalid credentials"))
        
        user_id = auth_response.get("user", {}).get("id")
        
        if not user_id:
            raise UnauthorizedError("Invalid credentials")
        
        # Get user profile
        profile_response = supabase_request(
            method="GET",
            endpoint=f"/rest/v1/profiles?id=eq.{user_id}",
        )
        
        if not profile_response or len(profile_response) == 0:
            # Create profile if it doesn't exist
            profile_data = {
                "id": user_id,
                "username": f"user_{generate_uuid()[:8]}",  # Generate temporary username
                "created_at": auth_response.get("user", {}).get("created_at"),
                "updated_at": auth_response.get("user", {}).get("created_at"),
            }
            
            supabase_request(
                method="POST",
                endpoint="/rest/v1/profiles",
                data=profile_data,
            )
            
            profile = profile_data
        else:
            profile = profile_response[0]
        
        # Generate tokens
        access_token = create_access_token(identity=user_id)
        refresh_token = create_refresh_token(identity=user_id)
        
        return jsonify({
            "message": "Login successful",
            "user": {
                "id": user_id,
                "email": email,
                "username": profile.get("username"),
                "full_name": profile.get("full_name"),
                "avatar_url": profile.get("avatar_url"),
            },
            "tokens": {
                "access_token": access_token,
                "refresh_token": refresh_token,
            }
        }), 200
        
    except Exception as e:
        if isinstance(e, (BadRequestError, UnauthorizedError, ValidationFailedError)):
            raise
        current_app.logger.error(f"Login error: {str(e)}")
        raise UnauthorizedError("Login failed")


@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    """
    Refresh access token.
    
    Returns:
        JSON: New access token
    """
    current_user = get_jwt_identity()
    access_token = create_access_token(identity=current_user)
    
    return jsonify({
        "access_token": access_token
    }), 200


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def get_user():
    """
    Get current user data.
    
    Returns:
        JSON: User data
    """
    current_user = get_jwt_identity()
    
    try:
        # Get user profile
        profile_response = supabase_request(
            method="GET",
            endpoint=f"/rest/v1/profiles?id=eq.{current_user}",
        )
        
        if not profile_response or len(profile_response) == 0:
            raise NotFoundError("User profile not found")
        
        profile = profile_response[0]
        
        # Get user email from Supabase Auth
        user_response = supabase_request(
            method="GET",
            endpoint=f"/auth/v1/user/{current_user}",
        )
        
        email = user_response.get("email", "")
        
        return jsonify({
            "id": current_user,
            "email": email,
            "username": profile.get("username"),
            "full_name": profile.get("full_name"),
            "bio": profile.get("bio"),
            "avatar_url": profile.get("avatar_url"),
            "country": profile.get("country"),
            "interests": profile.get("interests"),
            "conference_experience": profile.get("conference_experience"),
        }), 200
        
    except Exception as e:
        if isinstance(e, NotFoundError):
            raise
        current_app.logger.error(f"Error getting user data: {str(e)}")
        raise BadRequestError("Failed to get user data") 