"""
Utility functions for the application.
"""
import uuid
import os
import json
from functools import wraps
from flask import request, current_app
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
import requests
from supabase import create_client, Client
from app.core.errors import UnauthorizedError, ForbiddenError, RateLimitError


def generate_uuid():
    """Generate a UUID string."""
    return str(uuid.uuid4())


def create_supabase_client() -> Client:
    """
    Create and return a Supabase client instance.
    
    Returns:
        Client: Supabase client
        
    Raises:
        UnauthorizedError: If Supabase credentials are not configured
    """
    supabase_url = current_app.config["SUPABASE_URL"]
    supabase_key = current_app.config["SUPABASE_API_KEY"]
    
    if not supabase_url or not supabase_key:
        current_app.logger.error("Supabase credentials not configured")
        raise UnauthorizedError("API credentials not configured")
    
    return create_client(supabase_url, supabase_key)


def execute_mcp_query(query, params=None):
    """
    Execute a SQL query using MCP if available, otherwise fallback to Supabase.
    
    Args:
        query (str): SQL query to execute
        params (list, optional): Query parameters
        
    Returns:
        dict: Query results
        
    Raises:
        Exception: If query execution fails
    """
    try:
        # Try MCP execution if available via API
        mcp_server_url = os.environ.get("MCP_SERVER_URL")
        if mcp_server_url:
            response = requests.post(
                f"{mcp_server_url}/query",
                json={"query": query, "params": params or []}
            )
            if response.status_code == 200:
                return response.json()
        
        # Fallback to Supabase
        supabase = create_supabase_client()
        response = supabase.rpc('run_sql', {"query": query, "params": params or []}).execute()
        return response.data
    except Exception as e:
        current_app.logger.error(f"MCP query error: {str(e)}")
        raise


def supabase_request(method, endpoint, data=None, params=None, headers=None):
    """
    Make a request to the Supabase API using the supabase-py library.
    
    Args:
        method (str): HTTP method (GET, POST, PUT, PATCH, DELETE)
        endpoint (str): API endpoint
        data (dict, optional): Request data
        params (dict, optional): Query parameters
        headers (dict, optional): Request headers
        
    Returns:
        dict: Response data
        
    Raises:
        APIError: If the request fails
    """
    try:
        supabase = create_supabase_client()
        
        # Extract table and conditions from endpoint
        # Expected format: /rest/v1/table_name?condition=value
        parts = endpoint.strip('/').split('/')
        if len(parts) < 3 or parts[0] != 'rest' or parts[1] != 'v1':
            raise ValueError(f"Invalid endpoint format: {endpoint}")
        
        table_name = parts[2].split('?')[0]
        query = supabase.table(table_name)
        
        # Apply conditions if present in the endpoint
        if '?' in endpoint:
            conditions = endpoint.split('?')[1].split('&')
            for condition in conditions:
                if '=' in condition:
                    key, value = condition.split('=')
                    # Handle equality conditions (eq., neq., etc.)
                    if '.=' in key:
                        operator, field = key.split('.=')
                        if operator == 'eq':
                            query = query.eq(field, value)
                        elif operator == 'neq':
                            query = query.neq(field, value)
                        elif operator == 'gt':
                            query = query.gt(field, value)
                        elif operator == 'lt':
                            query = query.lt(field, value)
                        elif operator == 'gte':
                            query = query.gte(field, value)
                        elif operator == 'lte':
                            query = query.lte(field, value)
        
        # Execute the appropriate method on the query
        if method.upper() == 'GET':
            response = query.select('*').execute()
            return response.data
        elif method.upper() == 'POST':
            response = query.insert(data).execute()
            return response.data
        elif method.upper() in ['PUT', 'PATCH']:
            response = query.update(data).execute()
            return response.data
        elif method.upper() == 'DELETE':
            response = query.delete().execute()
            return response.data
        else:
            raise ValueError(f"Unsupported method: {method}")
            
    except Exception as e:
        current_app.logger.error(f"Supabase API error: {str(e)}")
        
        if "429" in str(e):
            raise RateLimitError("Too many requests to Supabase API")
        elif "401" in str(e):
            raise UnauthorizedError("Unauthorized access to Supabase API")
        elif "403" in str(e):
            raise ForbiddenError("Forbidden access to Supabase API")
        else:
            from app.core.errors import APIError
            raise APIError(
                message=f"Supabase API error: {str(e)}",
                status_code=500
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