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
        # Get user profile with improved error handling for schema changes
        try:
            profile_response = supabase_request(
                method="GET",
                endpoint=f"/rest/v1/profiles?id=eq.{current_user}",
            )
        except Exception as e:
            # If there's an issue with the request, try a more basic query
            current_app.logger.warning(f"Initial profile request failed: {str(e)}")
            supabase = create_supabase_client()
            result = supabase.table('profiles').select('id,username,full_name,bio,avatar_url,country,school,education_level,interests').eq('id', current_user).execute()
            profile_response = result.data
        
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
        school (str, optional): User's school
        education_level (str, optional): User's education level
        interests (list, optional): List of user's interests
        
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
        
        # Ensure we're not sending fields that might cause schema conflicts
        sanitized_data = {
            k: v for k, v in data.items() 
            if k in ['username', 'full_name', 'bio', 'avatar_url', 'country', 'school', 'education_level', 'interests']
        }
        
        # Check if username is being updated and if it already exists
        if "username" in sanitized_data:
            username = sanitized_data["username"]
            existing_user = supabase_request(
                method="GET",
                endpoint=f"/rest/v1/profiles?username=eq.{username}&id=neq.{current_user}",
            )
            
            if existing_user and len(existing_user) > 0:
                raise ConflictError("Username already exists")
        
        # Add updated timestamp
        sanitized_data['updated_at'] = 'now()'
        
        # Update profile in Supabase with better error handling
        try:
            update_response = supabase_request(
                method="PATCH",
                endpoint=f"/rest/v1/profiles?id=eq.{current_user}",
                data=sanitized_data
            )
        except Exception as e:
            # If the PATCH request fails, try a more targeted approach
            current_app.logger.warning(f"Initial update request failed: {str(e)}")
            supabase = create_supabase_client()
            update_response = supabase.table('profiles').update(sanitized_data).eq('id', current_user).execute()
        
        # Get updated profile
        try:
            profile_response = supabase_request(
                method="GET",
                endpoint=f"/rest/v1/profiles?id=eq.{current_user}",
            )
        except Exception as e:
            # If there's an issue with the request, try a more basic query
            current_app.logger.warning(f"Post-update profile request failed: {str(e)}")
            supabase = create_supabase_client()
            result = supabase.table('profiles').select('id,username,full_name,bio,avatar_url,country,school,education_level,interests').eq('id', current_user).execute()
            profile_response = result.data
        
        if not profile_response or len(profile_response) == 0:
            raise NotFoundError("User profile not found")
        
        profile = profile_response[0]
        
        # Serialize profile data
        result = profile_schema.dump(profile)
        
        return jsonify(result), 200
        
    except Exception as e:
        if isinstance(e, (NotFoundError, ConflictError, ValidationFailedError)):
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
        q (str, optional): Search query
        page (int, optional): Page number
        per_page (int, optional): Number of results per page
        
    Returns:
        JSON: Paginated list of user profiles
    """
    search_query = request.args.get("q", "")
    page = int(request.args.get("page", 1))
    per_page = min(int(request.args.get("per_page", 10)), 50)  # Limit to 50 max results
    
    try:
        # Build search query
        offset = (page - 1) * per_page
        
        # Try using the improved search approach with error handling
        try:
            # Use ilike for case-insensitive search
            search_condition = ""
            if search_query:
                search_condition = f"&or=(username.ilike.*{search_query}*,full_name.ilike.*{search_query}*)"
            
            profiles_response = supabase_request(
                method="GET",
                endpoint=f"/rest/v1/profiles?order=username{search_condition}&limit={per_page}&offset={offset}",
                headers={
                    "Range-Unit": "items",
                    "Range": f"{offset}-{offset+per_page-1}",
                    "Prefer": "count=exact"
                }
            )
            
            # Get total count from response headers
            total = 0
            
            # Since we're using the direct supabase_request, we don't have access to headers
            # We'll need to make a separate count query
            count_response = supabase_request(
                method="GET",
                endpoint=f"/rest/v1/profiles?select=count{search_condition}"
            )
            
            if count_response and len(count_response) > 0:
                total = count_response[0].get("count", 0)
            
        except Exception as e:
            # If there's an issue with the request, try using create_supabase_client directly
            current_app.logger.warning(f"Initial profiles search request failed: {str(e)}")
            supabase = create_supabase_client()
            
            # Build query
            query = supabase.table('profiles').select('id,username,full_name,bio,avatar_url,country,school,education_level,interests')
            
            # Apply search if provided
            if search_query:
                query = query.or_(f'username.ilike.%{search_query}%,full_name.ilike.%{search_query}%')
            
            # Get paginated results
            result = query.range(offset, offset + per_page - 1).execute()
            profiles_response = result.data
            
            # Get count
            count_result = supabase.table('profiles').select('count', count='exact')
            if search_query:
                count_result = count_result.or_(f'username.ilike.%{search_query}%,full_name.ilike.%{search_query}%')
            total = count_result.execute().count or 0
        
        # Calculate pagination metadata
        pages = (total + per_page - 1) // per_page if total > 0 else 0
        
        # Serialize profiles data
        profile_schema = ProfileSchema(many=True)
        profiles = profile_schema.dump(profiles_response)
        
        # Return paginated response
        response = {
            "data": profiles,
            "meta": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "pages": pages
            }
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        current_app.logger.error(f"Error searching profiles: {str(e)}")
        raise BadRequestError("Failed to search profiles") 