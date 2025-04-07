"""
Standardized Error Handler

This module provides consistent error handling across all MUN-Connect modules.
It defines standard error codes, formats, and utilities for handling exceptions.
"""

import json
import uuid
import traceback
import functools
from datetime import datetime
from typing import Dict, Any, Callable, TypeVar, Optional, Union, Type, cast

# Type variables for function decorators
F = TypeVar('F', bound=Callable[..., Any])
T = TypeVar('T')

# Standard error codes
class ErrorCode:
    """Standard error codes for MUN-Connect platform"""
    
    INVALID_INPUT = "INVALID_INPUT"
    MISSING_DEPENDENCY = "MISSING_DEPENDENCY"
    PROCESSING_ERROR = "PROCESSING_ERROR"
    MODEL_ERROR = "MODEL_ERROR"
    INTEGRATION_ERROR = "INTEGRATION_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    AUTHORIZATION_ERROR = "AUTHORIZATION_ERROR"
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    INTERNAL_ERROR = "INTERNAL_ERROR"

# Error messages
ERROR_MESSAGES = {
    ErrorCode.INVALID_INPUT: "Input validation failed",
    ErrorCode.MISSING_DEPENDENCY: "Required dependency not available",
    ErrorCode.PROCESSING_ERROR: "Error during processing",
    ErrorCode.MODEL_ERROR: "ML model error",
    ErrorCode.INTEGRATION_ERROR: "Module integration error",
    ErrorCode.DATABASE_ERROR: "Database operation error",
    ErrorCode.AUTHORIZATION_ERROR: "Authorization failed",
    ErrorCode.RESOURCE_NOT_FOUND: "Resource not found",
    ErrorCode.RATE_LIMIT_EXCEEDED: "Rate limit exceeded",
    ErrorCode.INTERNAL_ERROR: "Internal server error"
}

class MUNConnectError(Exception):
    """Base exception class for MUN-Connect errors"""
    
    def __init__(
        self, 
        code: str, 
        message: str, 
        details: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None
    ):
        """
        Initialize a MUN-Connect error
        
        Args:
            code: Error code (use ErrorCode constants)
            message: Human-readable error message
            details: Additional error details
            original_exception: Original exception that caused this error
        """
        self.code = code
        self.message = message
        self.details = details or {}
        self.original_exception = original_exception
        self.timestamp = datetime.now().isoformat()
        self.request_id = str(uuid.uuid4())
        
        # Include original exception info in details
        if original_exception:
            self.details["original_error"] = str(original_exception)
            self.details["original_type"] = type(original_exception).__name__
            
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert error to a dictionary
        
        Returns:
            Dictionary representation of the error
        """
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details,
                "timestamp": self.timestamp,
                "request_id": self.request_id
            }
        }
    
    def to_json(self) -> str:
        """
        Convert error to JSON string
        
        Returns:
            JSON representation of the error
        """
        return json.dumps(self.to_dict(), indent=2)

def create_error_response(
    code: str, 
    message: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    exception: Optional[Exception] = None
) -> Dict[str, Any]:
    """
    Create a standardized error response
    
    Args:
        code: Error code (use ErrorCode constants)
        message: Custom error message (if None, uses standard message for code)
        details: Additional error details
        exception: Original exception
        
    Returns:
        Dictionary with error information
    """
    # Use standard message if not provided
    if message is None:
        message = ERROR_MESSAGES.get(code, "Unknown error")
    
    # Create error object
    error = MUNConnectError(code, message, details, exception)
    
    return error.to_dict()

def handle_standard_exceptions(func: F) -> F:
    """
    Decorator for standardized exception handling
    
    This decorator catches common exceptions and returns standardized error responses.
    
    Args:
        func: Function to decorate
        
    Returns:
        Decorated function that handles exceptions
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValueError as e:
            return create_error_response(ErrorCode.INVALID_INPUT, str(e), exception=e)
        except ImportError as e:
            return create_error_response(ErrorCode.MISSING_DEPENDENCY, str(e), exception=e)
        except FileNotFoundError as e:
            return create_error_response(ErrorCode.RESOURCE_NOT_FOUND, str(e), exception=e)
        except PermissionError as e:
            return create_error_response(ErrorCode.AUTHORIZATION_ERROR, str(e), exception=e)
        except RuntimeError as e:
            return create_error_response(ErrorCode.PROCESSING_ERROR, str(e), exception=e)
        except Exception as e:
            # Get traceback information
            tb = traceback.format_exc()
            details = {"traceback": tb}
            return create_error_response(ErrorCode.INTERNAL_ERROR, str(e), details, exception=e)
    
    return cast(F, wrapper)

def catch_and_convert(
    exception_type: Union[Type[Exception], tuple],
    target_code: str,
    custom_message: Optional[str] = None
) -> Callable[[F], F]:
    """
    Decorator to catch specific exceptions and convert them to MUNConnectError
    
    Args:
        exception_type: Exception type(s) to catch
        target_code: Error code to use
        custom_message: Optional custom message (if None, uses exception message)
        
    Returns:
        Decorator function
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except exception_type as e:
                message = custom_message or str(e)
                raise MUNConnectError(target_code, message, original_exception=e)
        
        return cast(F, wrapper)
    
    return decorator 