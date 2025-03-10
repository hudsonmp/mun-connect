"""
User routes for profile management.
"""
from flask import request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.users import users_bp
from app.core.utils import supabase_request, rate_limit
from app.core.errors import (
    BadRequestError,
    NotFoundError,
    ValidationFailedError,
    ConflictError,
)
from app.core.schemas import ProfileSchema
from marshmallow import ValidationError


@users_bp.route("/profile", methods=["GET"])
@jwt_required()
def get_profile():
    """
    Get current user's profile.
    
    Returns:
        JSON: User profile data
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
        
        # Serialize profile data
        profile_schema = ProfileSchema()
        result = profile_schema.dump(profile)
        
        return jsonify(result), 200
        
    except Exception as e:
        if isinstance(e, NotFoundError):
            raise
        current_app.logger.error(f"Error getting profile: {str(e)}")
        raise BadRequestError("Failed to get profile")


@users_bp.route("/profile", methods=["PUT"])
@jwt_required()
@rate_limit(limit_per_minute=10)
def update_profile():
    """
    Update current user's profile.
    
    Request body:
        username (str, optional): User's username
        full_name (str, optional): User's full name
        bio (str, optional): User's bio
        avatar_url (str, optional): URL to user's avatar
        country (str, optional): User's country
        interests (list, optional): List of user's interests
        conference_experience (list, optional): List of user's conference experience
        
    Returns:
        JSON: Updated user profile data
    """
    current_user = get_jwt_identity()
    data = request.get_json()
    
    if not data:
        raise BadRequestError("No input data provided")
    
    try:
        # Validate input data
        profile_schema = ProfileSchema(partial=True)
        errors = profile_schema.validate(data)
        
        if errors:
            raise ValidationFailedError(f"Validation error: {errors}")
        
        # Check if username is being updated and if it already exists
        if "username" in data:
            username = data["username"]
            existing_user = supabase_request(
                method="GET",
                endpoint=f"/rest/v1/profiles?username=eq.{username}&id=neq.{current_user}",
            )
            
            if existing_user and len(existing_user) > 0:
                raise ConflictError("Username already exists")
        
        # Update profile in Supabase
        update_response = supabase_request(
            method="PATCH",
            endpoint=f"/rest/v1/profiles?id=eq.{current_user}",
            data={
                **data,
                "updated_at": "now()",
            },
        )
        
        # Get updated profile
        profile_response = supabase_request(
            method="GET",
            endpoint=f"/rest/v1/profiles?id=eq.{current_user}",
        )
        
        if not profile_response or len(profile_response) == 0:
            raise NotFoundError("User profile not found")
        
        profile = profile_response[0]
        
        # Serialize profile data
        result = profile_schema.dump(profile)
        
        return jsonify({
            "message": "Profile updated successfully",
            "profile": result,
        }), 200
        
    except Exception as e:
        if isinstance(e, (BadRequestError, NotFoundError, ValidationFailedError, ConflictError)):
            raise
        current_app.logger.error(f"Error updating profile: {str(e)}")
        raise BadRequestError("Failed to update profile")


@users_bp.route("/profile/<string:username>", methods=["GET"])
@rate_limit(limit_per_minute=30)
def get_user_profile(username):
    """
    Get a user's public profile by username.
    
    Args:
        username (str): Username to look up
        
    Returns:
        JSON: User profile data
    """
    try:
        # Get user profile
        profile_response = supabase_request(
            method="GET",
            endpoint=f"/rest/v1/profiles?username=eq.{username}",
        )
        
        if not profile_response or len(profile_response) == 0:
            raise NotFoundError("User profile not found")
        
        profile = profile_response[0]
        
        # Serialize profile data (exclude sensitive fields)
        profile_schema = ProfileSchema(exclude=["created_at", "updated_at"])
        result = profile_schema.dump(profile)
        
        return jsonify(result), 200
        
    except Exception as e:
        if isinstance(e, NotFoundError):
            raise
        current_app.logger.error(f"Error getting profile: {str(e)}")
        raise BadRequestError("Failed to get profile")


@users_bp.route("/profiles", methods=["GET"])
@rate_limit(limit_per_minute=10)
def search_profiles():
    """
    Search for user profiles.
    
    Query parameters:
        q (str, optional): Search query for username or full name
        country (str, optional): Filter by country
        interests (str, optional): Filter by interests (comma-separated)
        page (int, optional): Page number (default: 1)
        per_page (int, optional): Items per page (default: 20, max: 50)
        
    Returns:
        JSON: List of user profiles
    """
    try:
        # Get query parameters
        query = request.args.get("q", "")
        country = request.args.get("country", "")
        interests = request.args.get("interests", "").split(",") if request.args.get("interests") else []
        page = max(1, int(request.args.get("page", 1)))
        per_page = min(50, max(1, int(request.args.get("per_page", 20))))
        
        # Build query
        endpoint = "/rest/v1/profiles"
        params = {
            "select": "id,username,full_name,bio,avatar_url,country,interests,conference_experience",
            "order": "username.asc",
            "limit": per_page,
            "offset": (page - 1) * per_page,
        }
        
        # Add filters
        filters = []
        
        if query:
            filters.append(f"username.ilike.%{query}%,full_name.ilike.%{query}%")
        
        if country:
            filters.append(f"country.eq.{country}")
        
        if interests:
            for interest in interests:
                if interest:
                    filters.append(f"interests.cs.{{{interest}}}")
        
        if filters:
            params["or"] = "(" + ",".join(filters) + ")"
        
        # Get profiles
        profiles_response = supabase_request(
            method="GET",
            endpoint=endpoint,
            params=params,
        )
        
        # Get total count
        count_response = supabase_request(
            method="GET",
            endpoint=f"{endpoint}/count",
            params={"count": "exact"},
        )
        
        total = count_response.get("count", 0)
        
        # Serialize profiles
        profile_schema = ProfileSchema(exclude=["created_at", "updated_at"], many=True)
        results = profile_schema.dump(profiles_response)
        
        return jsonify({
            "data": results,
            "meta": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "pages": (total + per_page - 1) // per_page,
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error searching profiles: {str(e)}")
        raise BadRequestError("Failed to search profiles") 