"""
Utility functions for the application.
"""
import uuid
from functools import wraps
from flask import request, current_app
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
import requests
from app.core.errors import UnauthorizedError, ForbiddenError, RateLimitError


def generate_uuid():
    """Generate a UUID string."""
    return str(uuid.uuid4())


def supabase_request(method, endpoint, data=None, params=None, headers=None):
    """
    Make a request to the Supabase API.
    
    Args:
        method (str): HTTP method (GET, POST, PUT, DELETE)
        endpoint (str): API endpoint
        data (dict, optional): Request data
        params (dict, optional): Query parameters
        headers (dict, optional): Request headers
        
    Returns:
        dict: Response data
        
    Raises:
        APIError: If the request fails
    """
    base_url = current_app.config["SUPABASE_URL"]
    api_key = current_app.config["SUPABASE_KEY"]
    
    if not base_url or not api_key:
        current_app.logger.error("Supabase credentials not configured")
        raise UnauthorizedError("API credentials not configured")
    
    url = f"{base_url}{endpoint}"
    
    default_headers = {
        "apikey": api_key,
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    if headers:
        default_headers.update(headers)
    
    try:
        response = requests.request(
            method=method,
            url=url,
            json=data,
            params=params,
            headers=default_headers
        )
        
        if response.status_code == 429:
            raise RateLimitError("Too many requests to Supabase API")
        
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Supabase API error: {str(e)}")
        status_code = getattr(e.response, "status_code", 500)
        error_message = getattr(e.response, "text", str(e))
        
        if status_code == 401:
            raise UnauthorizedError("Unauthorized access to Supabase API")
        elif status_code == 403:
            raise ForbiddenError("Forbidden access to Supabase API")
        else:
            from app.core.errors import APIError
            raise APIError(
                message=f"Supabase API error: {error_message}",
                status_code=status_code
            )


def admin_required(fn):
    """
    Decorator to require admin role for a route.
    
    Args:
        fn: The function to decorate
        
    Returns:
        function: The decorated function
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        user_id = get_jwt_identity()
        
        # Check if user is admin in Supabase
        try:
            response = supabase_request(
                method="GET",
                endpoint=f"/rest/v1/profiles?id=eq.{user_id}&select=is_admin",
            )
            
            if not response or not response[0].get("is_admin"):
                raise ForbiddenError("Admin access required")
                
        except Exception as e:
            current_app.logger.error(f"Error checking admin status: {str(e)}")
            raise ForbiddenError("Admin access required")
            
        return fn(*args, **kwargs)
    return wrapper


def rate_limit(limit_per_minute=60):
    """
    Decorator to apply rate limiting to a route.
    
    Args:
        limit_per_minute (int): Maximum requests per minute
        
    Returns:
        function: The decorated function
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            # Get client IP
            client_ip = request.remote_addr
            
            # Use cache to track request count
            cache_key = f"rate_limit:{client_ip}:{request.path}"
            request_count = current_app.extensions["cache"].get(cache_key) or 0
            
            if request_count >= limit_per_minute:
                raise RateLimitError(f"Rate limit of {limit_per_minute} requests per minute exceeded")
            
            # Increment request count
            current_app.extensions["cache"].set(
                cache_key, 
                request_count + 1, 
                timeout=60  # Reset after 1 minute
            )
            
            return fn(*args, **kwargs)
        return wrapper
    return decorator 