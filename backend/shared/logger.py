"""
Standardized Logger

This module provides consistent logging capabilities across all MUN-Connect modules.
It configures logging with standardized formats, levels, and handlers.
"""

import os
import json
import logging
import logging.handlers
import uuid
import time
import threading
from datetime import datetime
from typing import Dict, Any, Optional, List, Union

# Default log level (can be overridden by environment variable)
DEFAULT_LOG_LEVEL = os.environ.get("MUN_LOG_LEVEL", "INFO")

# Default log directory
DEFAULT_LOG_DIR = os.environ.get("MUN_LOG_DIR", "logs")

# Configure log formatting
JSON_LOG_FORMAT = True  # Set to False to use text format instead of JSON

# Thread-local storage for request context
_thread_local = threading.local()

class RequestContext:
    """Context for the current request"""
    
    def __init__(self, request_id: Optional[str] = None, user_id: Optional[str] = None):
        """
        Initialize request context
        
        Args:
            request_id: Unique identifier for the request
            user_id: ID of the user making the request
        """
        self.request_id = request_id or str(uuid.uuid4())
        self.user_id = user_id
        self.start_time = time.time()
        self.metadata = {}  # Additional context data

def get_request_context() -> Optional[RequestContext]:
    """
    Get the current request context
    
    Returns:
        Current request context or None if not set
    """
    return getattr(_thread_local, "request_context", None)

def set_request_context(
    request_id: Optional[str] = None, 
    user_id: Optional[str] = None
) -> RequestContext:
    """
    Set the current request context
    
    Args:
        request_id: Unique identifier for the request
        user_id: ID of the user making the request
        
    Returns:
        Newly created request context
    """
    _thread_local.request_context = RequestContext(request_id, user_id)
    return _thread_local.request_context

def clear_request_context() -> None:
    """Clear the current request context"""
    if hasattr(_thread_local, "request_context"):
        delattr(_thread_local, "request_context")

class JSONFormatter(logging.Formatter):
    """Formatter that outputs JSON strings"""
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON
        
        Args:
            record: Log record to format
            
        Returns:
            JSON string representation of the log record
        """
        # Get the original message
        message = super().format(record)
        
        # Create log object with standard fields
        log_object = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "module": record.module,
            "message": message
        }
        
        # Add exception info if available
        if record.exc_info:
            log_object["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info)
            }
        
        # Add request context if available
        context = get_request_context()
        if context:
            log_object["request_id"] = context.request_id
            if context.user_id:
                log_object["user_id"] = context.user_id
            
            # Add duration for certain log levels
            if record.levelname in ("INFO", "WARNING", "ERROR", "CRITICAL"):
                duration_ms = int((time.time() - context.start_time) * 1000)
                log_object["duration_ms"] = duration_ms
            
            # Add additional context metadata
            for key, value in context.metadata.items():
                if key not in log_object:
                    log_object[key] = value
        
        # Add custom fields from the record
        if hasattr(record, "details") and record.details:
            log_object["details"] = record.details
        
        return json.dumps(log_object)

def setup_logger(
    name: str,
    log_level: Optional[str] = None,
    log_dir: Optional[str] = None,
    log_to_console: bool = True,
    log_to_file: bool = True,
    max_bytes: int = 10485760,  # 10MB
    backup_count: int = 5
) -> logging.Logger:
    """
    Set up a standardized logger
    
    Args:
        name: Logger name
        log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory for log files
        log_to_console: Whether to log to console
        log_to_file: Whether to log to file
        max_bytes: Maximum size of log file before rotation
        backup_count: Number of backup files to keep
        
    Returns:
        Configured logger
    """
    # Use default values if not provided
    log_level = log_level or DEFAULT_LOG_LEVEL
    log_dir = log_dir or DEFAULT_LOG_DIR
    
    # Convert log level string to constant
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Clear existing handlers
    logger.handlers = []
    
    # Create formatters
    if JSON_LOG_FORMAT:
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    # Add console handler if requested
    if log_to_console:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # Add file handler if requested
    if log_to_file:
        # Create log directory if needed
        os.makedirs(log_dir, exist_ok=True)
        
        # Create rotating file handler
        log_file = os.path.join(log_dir, f"{name}.log")
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger

class ExtendedLogger(logging.Logger):
    """Extended logger with additional methods for structured logging"""
    
    def __init__(self, name: str, level: int = logging.NOTSET):
        """
        Initialize extended logger
        
        Args:
            name: Logger name
            level: Initial log level
        """
        super().__init__(name, level)
    
    def log_with_details(
        self,
        level: int,
        msg: str,
        details: Dict[str, Any],
        *args,
        **kwargs
    ) -> None:
        """
        Log message with additional structured details
        
        Args:
            level: Log level
            msg: Log message
            details: Additional structured details
            *args: Additional positional arguments
            **kwargs: Additional keyword arguments
        """
        if self.isEnabledFor(level):
            # Add details to the record
            extra = kwargs.get("extra", {})
            extra["details"] = details
            kwargs["extra"] = extra
            
            self._log(level, msg, args, **kwargs)
    
    def info_with_details(self, msg: str, details: Dict[str, Any], *args, **kwargs) -> None:
        """Log info message with additional structured details"""
        self.log_with_details(logging.INFO, msg, details, *args, **kwargs)
    
    def warning_with_details(self, msg: str, details: Dict[str, Any], *args, **kwargs) -> None:
        """Log warning message with additional structured details"""
        self.log_with_details(logging.WARNING, msg, details, *args, **kwargs)
    
    def error_with_details(self, msg: str, details: Dict[str, Any], *args, **kwargs) -> None:
        """Log error message with additional structured details"""
        self.log_with_details(logging.ERROR, msg, details, *args, **kwargs)
    
    def critical_with_details(self, msg: str, details: Dict[str, Any], *args, **kwargs) -> None:
        """Log critical message with additional structured details"""
        self.log_with_details(logging.CRITICAL, msg, details, *args, **kwargs)

# Register the extended logger class
logging.setLoggerClass(ExtendedLogger)

def get_logger(name: str) -> ExtendedLogger:
    """
    Get a standardized logger
    
    This is the main function to use for getting a logger in any module.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Configured ExtendedLogger
    """
    logger = logging.getLogger(name)
    
    # Return proper type
    return logger

# Initialize root logger
setup_logger("mun_connect") 