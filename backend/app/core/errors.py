"""
Error handling module for consistent API error responses.
"""
from flask import jsonify
from werkzeug.exceptions import HTTPException
from marshmallow import ValidationError
from jwt.exceptions import PyJWTError


class APIError(Exception):
    """Base class for API errors."""
    status_code = 500
    message = "An unexpected error occurred."
    error_code = "internal_server_error"
    
    def __init__(self, message=None, status_code=None, error_code=None, payload=None):
        super().__init__()
        if message is not None:
            self.message = message
        if status_code is not None:
            self.status_code = status_code
        if error_code is not None:
            self.error_code = error_code
        self.payload = payload
    
    def to_dict(self):
        rv = dict(self.payload or {})
        rv["error"] = {
            "code": self.error_code,
            "message": self.message
        }
        return rv


class BadRequestError(APIError):
    """400 Bad Request Error."""
    status_code = 400
    message = "Bad request."
    error_code = "bad_request"


class UnauthorizedError(APIError):
    """401 Unauthorized Error."""
    status_code = 401
    message = "Authentication required."
    error_code = "unauthorized"


class ForbiddenError(APIError):
    """403 Forbidden Error."""
    status_code = 403
    message = "Access forbidden."
    error_code = "forbidden"


class NotFoundError(APIError):
    """404 Not Found Error."""
    status_code = 404
    message = "Resource not found."
    error_code = "not_found"


class ConflictError(APIError):
    """409 Conflict Error."""
    status_code = 409
    message = "Resource conflict."
    error_code = "conflict"


class ValidationFailedError(APIError):
    """422 Validation Failed Error."""
    status_code = 422
    message = "Validation failed."
    error_code = "validation_failed"


class RateLimitError(APIError):
    """429 Rate Limit Error."""
    status_code = 429
    message = "Rate limit exceeded."
    error_code = "rate_limit_exceeded"


def register_error_handlers(app):
    """Register error handlers for the Flask app."""
    
    @app.errorhandler(APIError)
    def handle_api_error(error):
        response = jsonify(error.to_dict())
        response.status_code = error.status_code
        return response
    
    @app.errorhandler(ValidationError)
    def handle_validation_error(error):
        return jsonify({
            "error": {
                "code": "validation_failed",
                "message": "Validation failed.",
                "details": error.messages
            }
        }), 422
    
    @app.errorhandler(PyJWTError)
    def handle_jwt_error(error):
        return jsonify({
            "error": {
                "code": "unauthorized",
                "message": "Invalid or expired token."
            }
        }), 401
    
    @app.errorhandler(404)
    def handle_not_found(error):
        return jsonify({
            "error": {
                "code": "not_found",
                "message": "Resource not found."
            }
        }), 404
    
    @app.errorhandler(500)
    def handle_internal_server_error(error):
        return jsonify({
            "error": {
                "code": "internal_server_error",
                "message": "An unexpected error occurred."
            }
        }), 500
    
    @app.errorhandler(HTTPException)
    def handle_http_exception(error):
        return jsonify({
            "error": {
                "code": str(error.code),
                "message": error.description
            }
        }), error.code 