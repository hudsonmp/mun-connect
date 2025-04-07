"""
Shared Module

This package provides shared utilities, standardized logging, and error handling
for the MUN-Connect platform. These modules ensure consistent integration between
different components of the platform.
"""

import os

# Create necessary directories
os.makedirs('logs', exist_ok=True)

# Import key modules to make them available when importing the shared package
from .logger import get_logger, setup_logger, set_request_context, clear_request_context
from .error_handler import (
    ErrorCode, MUNConnectError, create_error_response, 
    handle_standard_exceptions, catch_and_convert
)

# AI interfaces and utilities
from .ai_interface import (
    AIInterface, AIProvider, OpenAIProvider, 
    AnthropicProvider, LocalModelProvider
)

# Version
__version__ = '0.1.0' 