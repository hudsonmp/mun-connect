#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Document Processing API

This module provides an AWS Lambda API Gateway implementation for the document processing pipeline.
"""

import os
import json
import uuid
import logging
import base64
import boto3
import botocore
from typing import Dict, List, Any, Optional, Tuple, Union

# AWS X-Ray SDK for tracing
from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.core import patch_all

# Conditionally import Flask for local testing
try:
    from flask import Flask, request, jsonify, send_from_directory
    from werkzeug.utils import secure_filename
    flask_available = True
except ImportError:
    flask_available = False

from document_processing_pipeline import DocumentProcessingPipeline
import config

# Configure logging for CloudWatch
log_level = os.environ.get('LOG_LEVEL', 'INFO')
numeric_level = getattr(logging, log_level.upper(), None)
if not isinstance(numeric_level, int):
    numeric_level = logging.INFO

logging.basicConfig(
    level=numeric_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize AWS X-Ray if enabled
if os.environ.get('XRAY_ENABLED', 'false').lower() == 'true':
    try:
        logger.info("Initializing AWS X-Ray")
        patch_all()
    except Exception as e:
        logger.warning(f"Failed to initialize X-Ray: {e}")

# Initialize S3 client
try:
    s3_client = boto3.client('s3')
    logger.info("Initialized S3 client")
except Exception as e:
    logger.error(f"Failed to initialize S3 client: {e}")
    s3_client = None

# Setup environment variables
USE_S3 = os.environ.get('USE_S3', 'true').lower() == 'true'
S3_BUCKET = os.environ.get('S3_BUCKET', 'document-processor-files')
TEST_ENV = os.environ.get('TEST_ENV', 'false').lower() == 'true'

# Initialize processing pipeline
def get_pipeline():
    """Get or create the document processing pipeline"""
    # Use smaller/faster models for testing
    if TEST_ENV:
        logger.info("Using test configuration for pipeline")
        return DocumentProcessingPipeline(
            use_markdown=config.PROCESSING_OPTIONS["use_markdown"],
            use_spacy=config.PROCESSING_OPTIONS["use_spacy"],
            use_transformers=False,  # Disable transformers for faster testing
            parallel_processing=False,  # Disable parallel processing for testing
            bert_model="distilbert-base-uncased",  # Use smaller model
            component_model=config.MODELS["argument_component"]["test"],
            relation_model=config.MODELS["argument_relation"]["test"],
            reasoning_model=config.MODELS["reasoning"]["test"],
            use_gpu=False,
            output_dir="/tmp" if USE_S3 else config.OUTPUT_DIR
        )
    else:
        return DocumentProcessingPipeline(
            use_markdown=config.PROCESSING_OPTIONS["use_markdown"],
            use_spacy=config.PROCESSING_OPTIONS["use_spacy"],
            use_transformers=config.PROCESSING_OPTIONS["use_transformers"],
            parallel_processing=config.PROCESSING_OPTIONS["parallel_processing"],
            bert_model=config.MODELS["bert"]["default"],
            component_model=config.MODELS["argument_component"]["default"],
            relation_model=config.MODELS["argument_relation"]["default"],
            reasoning_model=config.MODELS["reasoning"]["default"],
            use_gpu=config.PROCESSING_OPTIONS["use_gpu"],
            output_dir="/tmp" if USE_S3 else config.OUTPUT_DIR
        )

# Use lazy initialization for the pipeline to avoid cold starts
pipeline = None

def get_initialized_pipeline():
    """Lazily initialize the pipeline"""
    global pipeline
    if pipeline is None:
        pipeline = get_pipeline()
    return pipeline

def allowed_file(filename: str) -> bool:
    """
    Check if the file has an allowed extension.
    
    Args:
        filename: Name of the file
        
    Returns:
        Whether the file has an allowed extension
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in config.API_CONFIG["allowed_extensions"]

# S3 utility functions
def upload_to_s3(file_path: str, s3_key: str) -> str:
    """
    Upload a file to S3.
    
    Args:
        file_path: Path to the local file
        s3_key: S3 object key
        
    Returns:
        S3 URI
    """
    try:
        s3_client.upload_file(file_path, S3_BUCKET, s3_key)
        logger.info(f"Uploaded {file_path} to s3://{S3_BUCKET}/{s3_key}")
        return f"s3://{S3_BUCKET}/{s3_key}"
    except botocore.exceptions.ClientError as e:
        logger.error(f"Error uploading to S3: {e}")
        raise

def download_from_s3(s3_key: str, local_path: str) -> str:
    """
    Download a file from S3.
    
    Args:
        s3_key: S3 object key
        local_path: Path to save the file locally
        
    Returns:
        Local file path
    """
    try:
        s3_client.download_file(S3_BUCKET, s3_key, local_path)
        logger.info(f"Downloaded s3://{S3_BUCKET}/{s3_key} to {local_path}")
        return local_path
    except botocore.exceptions.ClientError as e:
        logger.error(f"Error downloading from S3: {e}")
        raise

def get_s3_presigned_url(s3_key: str, expiration: int = 3600) -> str:
    """
    Generate a presigned URL for an S3 object.
    
    Args:
        s3_key: S3 object key
        expiration: URL expiration time in seconds
        
    Returns:
        Presigned URL
    """
    try:
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': S3_BUCKET, 'Key': s3_key},
            ExpiresIn=expiration
        )
        return url
    except botocore.exceptions.ClientError as e:
        logger.error(f"Error generating presigned URL: {e}")
        raise

def save_file_from_request(file_data: Union[bytes, Any], filename: str) -> Tuple[str, str]:
    """
    Save a file from a request to local storage or S3.
    
    Args:
        file_data: File data (bytes or file-like object)
        filename: Original filename
        
    Returns:
        Tuple of (file path or S3 URI, unique filename)
    """
    # Generate unique filename
    unique_id = str(uuid.uuid4())
    secure_name = secure_filename(filename) if 'secure_filename' in globals() else filename.replace(' ', '_')
    filename_parts = secure_name.rsplit('.', 1)
    unique_filename = f"{filename_parts[0]}_{unique_id}.{filename_parts[1]}"
    
    # Save file locally
    if USE_S3:
        temp_path = os.path.join("/tmp", unique_filename)
    else:
        temp_path = os.path.join(config.API_CONFIG["upload_folder"], unique_filename)
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(temp_path), exist_ok=True)
    
    # Write file data
    if hasattr(file_data, 'save'):  # Flask FileStorage object
        file_data.save(temp_path)
    else:  # Bytes data from Lambda event
        with open(temp_path, 'wb') as f:
            f.write(file_data)
    
    # Upload to S3 if configured
    if USE_S3:
        s3_key = f"uploads/{unique_filename}"
        s3_uri = upload_to_s3(temp_path, s3_key)
        return s3_uri, unique_filename
    else:
        return temp_path, unique_filename

def process_document_handler(event, context=None):
    """
    AWS Lambda handler for processing a document.
    
    Args:
        event: Lambda event
        context: Lambda context
        
    Returns:
        Lambda response
    """
    logger.info("Processing document request")
    
    try:
        # Check if this is API Gateway event
        if isinstance(event, dict) and event.get('httpMethod') == 'POST':
            # Extract file from event
            if 'body' not in event:
                return {
                    'statusCode': 400,
                    'body': json.dumps({
                        'success': False,
                        'error': 'No file provided'
                    })
                }
            
            # Handle multipart/form-data
            if event.get('isBase64Encoded', False):
                # Decode base64 body
                body_decoded = base64.b64decode(event['body'])
                
                # Parse multipart form data (simplified - in practice use a library)
                # This is a placeholder - in production, use proper multipart parser
                file_data = body_decoded
                original_filename = event.get('queryStringParameters', {}).get('filename', 'document.pdf')
                document_type = event.get('queryStringParameters', {}).get('document_type')
            else:
                # For direct JSON payload (non-multipart)
                body = json.loads(event['body'])
                if 'file' not in body or 'filename' not in body:
                    return {
                        'statusCode': 400,
                        'body': json.dumps({
                            'success': False,
                            'error': 'No file provided in request body'
                        })
                    }
                
                # Decode base64 file content
                file_data = base64.b64decode(body['file'])
                original_filename = body['filename']
                document_type = body.get('document_type')
            
            # Validate file type
            if not allowed_file(original_filename):
                return {
                    'statusCode': 400,
                    'body': json.dumps({
                        'success': False,
                        'error': 'Invalid file type, only PDF files are allowed'
                    })
                }
            
            # Save file
            file_path, unique_filename = save_file_from_request(file_data, original_filename)
            
            # If file was saved to S3, download it to process
            if file_path.startswith('s3://'):
                s3_key = file_path.replace(f"s3://{S3_BUCKET}/", '')
                local_path = os.path.join("/tmp", unique_filename)
                file_path = download_from_s3(s3_key, local_path)
            
            # Process document
            pipeline = get_initialized_pipeline()
            output_path, document_data = pipeline.process_document(file_path, document_type)
            
            # Generate profile
            profile = pipeline.extract_profile(document_data)
            
            # If S3 is enabled, upload the output file and generate a presigned URL
            if USE_S3:
                output_filename = os.path.basename(output_path)
                s3_key = f"output/{output_filename}"
                upload_to_s3(output_path, s3_key)
                download_url = get_s3_presigned_url(s3_key)
            else:
                download_url = f"/download/{os.path.basename(output_path)}"
            
            # Create response
            response = {
                'success': True,
                'file_id': unique_filename.split('_')[-1].split('.')[0],
                'original_filename': original_filename,
                'document_type': document_data["metadata"]["document_type"],
                'output_file': os.path.basename(output_path),
                'download_url': download_url,
                'profile': profile,
                'metadata': document_data["metadata"]
            }
            
            return {
                'statusCode': 200,
                'body': json.dumps(response),
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Credentials': True
                }
            }
    
    except Exception as e:
        logger.error(f"Error processing document: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'success': False,
                'error': str(e)
            }),
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Credentials': True
            }
        }

def process_batch_handler(event, context=None):
    """
    AWS Lambda handler for processing multiple documents.
    
    Args:
        event: Lambda event
        context: Lambda context
        
    Returns:
        Lambda response
    """
    logger.info("Processing batch request")
    
    try:
        # Extract files from event
        if not isinstance(event, dict) or 'body' not in event:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'success': False,
                    'error': 'No files provided'
                })
            }
        
        # Parse request body
        body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
        
        if 'files' not in body:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'success': False,
                    'error': 'No files provided in request body'
                })
            }
        
        files = body['files']
        
        # Check if files list is empty
        if not files or len(files) == 0:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'success': False,
                    'error': 'No files selected'
                })
            }
        
        # Process each file
        results = []
        file_paths = []
        
        for file_entry in files:
            if 'file' not in file_entry or 'filename' not in file_entry:
                continue
            
            # Decode base64 file content
            file_data = base64.b64decode(file_entry['file'])
            original_filename = file_entry['filename']
            
            # Validate file type
            if not allowed_file(original_filename):
                continue
            
            # Save file
            file_path, unique_filename = save_file_from_request(file_data, original_filename)
            
            # If file was saved to S3, download it to process
            if file_path.startswith('s3://'):
                s3_key = file_path.replace(f"s3://{S3_BUCKET}/", '')
                local_path = os.path.join("/tmp", unique_filename)
                file_path = download_from_s3(s3_key, local_path)
            
            file_paths.append(file_path)
        
        # Process all documents
        pipeline = get_initialized_pipeline()
        processed_results = pipeline.process_multiple_documents(file_paths)
        
        # Generate profiles
        profiles = []
        processed_files = []
        
        for output_path, document_data in processed_results:
            profile = pipeline.extract_profile(document_data)
            profiles.append(profile)
            
            # If S3 is enabled, upload the output file and generate a presigned URL
            if USE_S3:
                output_filename = os.path.basename(output_path)
                s3_key = f"output/{output_filename}"
                upload_to_s3(output_path, s3_key)
                download_url = get_s3_presigned_url(s3_key)
            else:
                download_url = f"/download/{os.path.basename(output_path)}"
            
            processed_files.append({
                'original_filename': os.path.basename(document_data["metadata"]["file_path"]),
                'document_type': document_data["metadata"]["document_type"],
                'output_file': os.path.basename(output_path),
                'download_url': download_url
            })
        
        # Generate aggregate profile
        aggregate_profile = pipeline.aggregate_profiles(profiles)
        
        # Create response
        response = {
            'success': True,
            'file_count': len(processed_files),
            'files': processed_files,
            'aggregate_profile': aggregate_profile
        }
        
        return {
            'statusCode': 200,
            'body': json.dumps(response),
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Credentials': True
            }
        }
    
    except Exception as e:
        logger.error(f"Error processing batch: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'success': False,
                'error': str(e)
            }),
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Credentials': True
            }
        }

def download_file_handler(event, context=None):
    """
    AWS Lambda handler for downloading a file.
    
    Args:
        event: Lambda event
        context: Lambda context
        
    Returns:
        Lambda response
    """
    logger.info("Download file request")
    
    try:
        # Extract filename from path parameters
        if not isinstance(event, dict) or 'pathParameters' not in event or 'filename' not in event['pathParameters']:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'success': False,
                    'error': 'No filename provided'
                })
            }
        
        filename = event['pathParameters']['filename']
        
        # If S3 is enabled, generate a presigned URL
        if USE_S3:
            s3_key = f"output/{filename}"
            try:
                download_url = get_s3_presigned_url(s3_key)
                
                # Return redirect to presigned URL
                return {
                    'statusCode': 302,
                    'headers': {
                        'Location': download_url,
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Credentials': True
                    },
                    'body': ''
                }
            except Exception as e:
                logger.error(f"Error generating presigned URL: {e}")
                return {
                    'statusCode': 404,
                    'body': json.dumps({
                        'success': False,
                        'error': f"File not found: {filename}"
                    })
                }
        
        # If local storage, this would be handled by Flask but not in Lambda
        return {
            'statusCode': 400,
            'body': json.dumps({
                'success': False,
                'error': 'Direct file download not supported in Lambda, use S3 presigned URLs'
            })
        }
    
    except Exception as e:
        logger.error(f"Error downloading file: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'success': False,
                'error': str(e)
            })
        }

def health_check_handler(event, context=None):
    """
    AWS Lambda handler for health check.
    
    Args:
        event: Lambda event
        context: Lambda context
        
    Returns:
        Lambda response
    """
    logger.info("Health check request")
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'status': 'healthy',
            'version': '1.0.0',
            'environment': 'test' if TEST_ENV else 'production',
            's3_enabled': USE_S3
        }),
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Credentials': True
        }
    }

# Main Lambda handler function
def lambda_handler(event, context):
    """
    AWS Lambda handler routing requests to the appropriate handler.
    
    Args:
        event: Lambda event
        context: Lambda context
        
    Returns:
        Lambda response
    """
    logger.info(f"Received event: {json.dumps(event)}")
    
    # Route based on path and method
    path = event.get('path', '')
    method = event.get('httpMethod', '').upper()
    
    # If path is null or empty, try to determine from API Gateway requestContext
    if not path and 'requestContext' in event and 'path' in event['requestContext']:
        path = event['requestContext']['path']
    
    # Route to appropriate handler
    if path == '/process' and method == 'POST':
        return process_document_handler(event, context)
    elif path == '/process-batch' and method == 'POST':
        return process_batch_handler(event, context)
    elif path.startswith('/download/') and method == 'GET':
        return download_file_handler(event, context)
    elif path == '/health' and method == 'GET':
        return health_check_handler(event, context)
    else:
        return {
            'statusCode': 404,
            'body': json.dumps({
                'success': False,
                'error': f"Route not found: {method} {path}"
            }),
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Credentials': True
            }
        }

# Flask app for local testing
if flask_available:
    app = Flask(__name__)
    app.config['UPLOAD_FOLDER'] = config.API_CONFIG["upload_folder"]
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
    
    # Create a test client for local testing
    class TestClient:
        """Test client for the API"""
        
        @staticmethod
        def mock_event(path, method, body=None, path_params=None, query_params=None):
            """Create a mock Lambda event"""
            event = {
                'path': path,
                'httpMethod': method,
                'headers': {
                    'Content-Type': 'application/json'
                },
                'pathParameters': path_params or {},
                'queryStringParameters': query_params or {},
                'body': json.dumps(body) if body else None
            }
            return event
        
        @staticmethod
        def invoke(path, method, body=None, path_params=None, query_params=None):
            """Invoke the Lambda handler with a mock event"""
            event = TestClient.mock_event(path, method, body, path_params, query_params)
            return lambda_handler(event, None)
        
        @staticmethod
        def generate_mock_pdf():
            """Generate a mock PDF file for testing"""
            import io
            from reportlab.pdfgen import canvas
            
            buffer = io.BytesIO()
            c = canvas.Canvas(buffer)
            c.drawString(100, 100, "Test Document")
            c.save()
            
            buffer.seek(0)
            return buffer.read()
    
    # Map Flask routes to Lambda handlers for local testing
    @app.route('/process', methods=['POST'])
    def process_document():
        """Flask route for processing a document"""
        try:
            # Check if file is included in request
            if 'file' not in request.files:
                return jsonify({
                    'success': False,
                    'error': 'No file provided'
                }), 400
            
            file = request.files['file']
            
            # Check if file is empty
            if file.filename == '':
                return jsonify({
                    'success': False,
                    'error': 'No file selected'
                }), 400
            
            # Simulate Lambda handler
            event = {
                'httpMethod': 'POST',
                'path': '/process',
                'queryStringParameters': {
                    'document_type': request.form.get('document_type'),
                    'filename': file.filename
                },
                'body': base64.b64encode(file.read()).decode('utf-8'),
                'isBase64Encoded': True
            }
            
            result = lambda_handler(event, None)
            
            if result['statusCode'] == 200:
                return jsonify(json.loads(result['body'])), 200
            else:
                return jsonify(json.loads(result['body'])), result['statusCode']
        
        except Exception as e:
            logger.error(f"Error in Flask route: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/process-batch', methods=['POST'])
    def process_batch():
        """Flask route for processing a batch of documents"""
        try:
            files = request.files.getlist('files[]')
            
            if not files or len(files) == 0:
                return jsonify({
                    'success': False,
                    'error': 'No files provided'
                }), 400
            
            # Convert files to base64 for Lambda handler
            files_data = []
            for file in files:
                if file.filename == '':
                    continue
                
                file_data = {
                    'filename': file.filename,
                    'file': base64.b64encode(file.read()).decode('utf-8')
                }
                files_data.append(file_data)
            
            # Simulate Lambda handler
            event = {
                'httpMethod': 'POST',
                'path': '/process-batch',
                'body': json.dumps({
                    'files': files_data
                })
            }
            
            result = lambda_handler(event, None)
            
            if result['statusCode'] == 200:
                return jsonify(json.loads(result['body'])), 200
            else:
                return jsonify(json.loads(result['body'])), result['statusCode']
        
        except Exception as e:
            logger.error(f"Error in Flask route: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/download/<filename>', methods=['GET'])
    def download_file(filename):
        """Flask route for downloading a file"""
        # Simulate Lambda handler
        event = {
            'httpMethod': 'GET',
            'path': f'/download/{filename}',
            'pathParameters': {
                'filename': filename
            }
        }
        
        result = lambda_handler(event, None)
        
        if result['statusCode'] == 302:
            # Redirect to presigned URL
            return f"Redirect to: {result['headers']['Location']}", 302
        elif 'OUTPUT_DIR' in config and os.path.exists(os.path.join(config.OUTPUT_DIR, filename)):
            # Fallback to direct file serving if S3 is not enabled
            return send_from_directory(
                config.OUTPUT_DIR, 
                filename,
                as_attachment=True
            )
        else:
            return jsonify(json.loads(result['body'])), result['statusCode']
    
    @app.route('/health', methods=['GET'])
    def health_check():
        """Flask route for health check"""
        event = {
            'httpMethod': 'GET',
            'path': '/health'
        }
        
        result = lambda_handler(event, None)
        return jsonify(json.loads(result['body'])), result['statusCode']

# Run the Flask app for local testing
if __name__ == '__main__' and flask_available:
    app.run(
        host=config.API_CONFIG["host"],
        port=config.API_CONFIG["port"],
        debug=config.API_CONFIG["debug"]
    )
