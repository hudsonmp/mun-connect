#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Container entry point for DelegateAnalyzer application.

This script starts a Flask server that exposes the DelegateAnalyzer
functionality as a REST API. It handles requests from ECS/Fargate
or other container orchestration services.
"""

import os
import json
import logging
import tempfile
import time
import sys
from typing import Dict, Any, Optional
from flask import Flask, request, jsonify

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger("delegate-analyzer-container")

# Import the delegate analyzer
from delegate_analyzer import get_analyzer_instance, container_handler

# Initialize Flask app
app = Flask(__name__)

# Environment variables
PORT = int(os.environ.get("PORT", 8080))
HEALTH_CHECK_PATH = os.environ.get("HEALTH_CHECK_PATH", "/health")
ANALYZER_PATH = os.environ.get("ANALYZER_PATH", "/analyze")

# Initialize analyzer at startup (outside of request handlers)
logger.info("Initializing DelegateAnalyzer instance at container startup")
analyzer = get_analyzer_instance()

@app.route(HEALTH_CHECK_PATH, methods=["GET"])
def health_check():
    """Health check endpoint for container orchestration"""
    return jsonify({"status": "healthy", "timestamp": time.time()})

@app.route(ANALYZER_PATH, methods=["POST"])
def analyze():
    """Main analysis endpoint"""
    try:
        # Get request JSON
        request_json = request.get_json()
        
        if not request_json:
            return jsonify({
                "status": "error",
                "error": "Missing JSON request body"
            }), 400
        
        # Process request
        result = container_handler(request_json)
        
        # Return result
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}", exc_info=True)
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

@app.route("/", methods=["GET"])
def index():
    """Root endpoint with basic information"""
    return jsonify({
        "name": "DelegateAnalyzer API",
        "version": "1.0.0",
        "description": "API for analyzing Model UN delegate documents",
        "endpoints": {
            "health": HEALTH_CHECK_PATH,
            "analyze": ANALYZER_PATH
        }
    })

if __name__ == "__main__":
    logger.info(f"Starting DelegateAnalyzer API server on port {PORT}")
    app.run(host="0.0.0.0", port=PORT) 