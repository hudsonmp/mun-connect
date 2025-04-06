#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Multi-Document Generator API

This module provides a Flask API for generating different types of UN documents
(position papers, speeches, and resolutions) that mimic a delegate's style.
It supports deployment as both a Flask app and AWS Lambda function.
"""

import os
import json
import uuid
import logging
import tempfile
import base64
from typing import Dict, List, Any, Optional, Tuple
import boto3
from botocore.exceptions import ClientError
import time
import traceback

from flask import Flask, request, jsonify, send_from_directory, Response
from werkzeug.utils import secure_filename

from multi_document_generator import MultiDocumentGenerator
import config

# Configure logging for both local and AWS environments
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Environment variables
ENV_S3_BUCKET = os.environ.get("DOCUMENT_GENERATOR_S3_BUCKET")
ENV_S3_REGION = os.environ.get("DOCUMENT_GENERATOR_S3_REGION", "us-east-1")
ENV_USE_S3 = os.environ.get("USE_S3", "false").lower() == "true"
ENV_TEST_MODE = os.environ.get("TEST_ENV", "false").lower() == "true"
ENV_XRAY_ENABLED = os.environ.get("XRAY_ENABLED", "false").lower() == "true"

# Check if running in Lambda environment
IS_LAMBDA = os.environ.get("AWS_LAMBDA_FUNCTION_NAME") is not None
IS_AWS = IS_LAMBDA or ENV_USE_S3

# Set up AWS X-Ray tracing if enabled
if ENV_XRAY_ENABLED:
    try:
        from aws_xray_sdk.core import xray_recorder
        from aws_xray_sdk.ext.flask.middleware import XRayMiddleware
        
        xray_recorder.configure(
            service='document-generator-api',
            context_missing='LOG_ERROR'
        )
        logger.info("AWS X-Ray tracing enabled")
    except ImportError:
        logger.warning("aws_xray_sdk not installed, X-Ray tracing disabled")
        ENV_XRAY_ENABLED = False

# Initialize Flask app
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = config.API_CONFIG.get("upload_folder", "uploads")
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Add X-Ray middleware if enabled
if ENV_XRAY_ENABLED and not ENV_TEST_MODE:
    XRayMiddleware(app, xray_recorder)

# Initialize S3 client if in AWS environment
s3_client = None
if IS_AWS or ENV_USE_S3:
    try:
        s3_client = boto3.client('s3', region_name=ENV_S3_REGION)
        logger.info(f"Initialized S3 client for region {ENV_S3_REGION}")
    except Exception as e:
        logger.error(f"Error initializing S3 client: {str(e)}")

# Ensure directories exist for local development
if not IS_LAMBDA:
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(config.GENERATOR_CONFIG.get("output_dir", "generated_documents"), exist_ok=True)

# Initialize generator (singleton pattern)
_generator_instance = None

def get_generator_instance():
    """Get or create the generator instance"""
    global _generator_instance
    if _generator_instance is None:
        _generator_instance = MultiDocumentGenerator(
            model_name=config.GENERATOR_CONFIG.get("model_name", "mistralai/Mistral-7B-Instruct-v0.2"),
            output_dir=config.GENERATOR_CONFIG.get("output_dir", "generated_documents"),
            use_gpu=config.GENERATOR_CONFIG.get("use_gpu", False),
            max_length=config.GENERATOR_CONFIG.get("max_length", 2048),
            temperature=config.GENERATOR_CONFIG.get("temperature", 0.7),
            top_p=config.GENERATOR_CONFIG.get("top_p", 0.9),
            seed=config.GENERATOR_CONFIG.get("seed", 42)
        )
    return _generator_instance

# S3 Helper Functions
def save_file_to_s3(file_data, bucket, key, content_type='application/json'):
    """Save file to S3 bucket"""
    if not s3_client:
        raise ValueError("S3 client not initialized")
    
    try:
        s3_client.put_object(
            Bucket=bucket,
            Key=key,
            Body=file_data,
            ContentType=content_type
        )
        logger.info(f"Successfully uploaded file to s3://{bucket}/{key}")
        return f"s3://{bucket}/{key}"
    except Exception as e:
        logger.error(f"Error uploading file to S3: {str(e)}")
        raise

def get_file_from_s3(bucket, key):
    """Download file from S3 bucket"""
    if not s3_client:
        raise ValueError("S3 client not initialized")
    
    try:
        response = s3_client.get_object(Bucket=bucket, Key=key)
        return response['Body'].read()
    except Exception as e:
        logger.error(f"Error downloading file from S3: {str(e)}")
        raise

def generate_presigned_url(bucket, key, expiration=3600):
    """Generate a presigned URL for an S3 object"""
    if not s3_client:
        raise ValueError("S3 client not initialized")
    
    try:
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': bucket,
                'Key': key
            },
            ExpiresIn=expiration
        )
        return url
    except Exception as e:
        logger.error(f"Error generating presigned URL: {str(e)}")
        raise

def allowed_file(filename: str) -> bool:
    """
    Check if the file has an allowed extension.
    
    Args:
        filename: Name of the file
        
    Returns:
        Whether the file has an allowed extension
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {"json"}


def _process_file_upload(request_data):
    """
    Process file upload from either multipart form or API Gateway format
    
    Args:
        request_data: Request data
        
    Returns:
        Tuple of (profile_data, profile_path)
    """
    # For Lambda + API Gateway requests with binary support enabled
    if IS_LAMBDA and 'isBase64Encoded' in request_data and request_data.get('isBase64Encoded'):
        try:
            # Decode base64 content
            content = base64.b64decode(request_data.get('body', ''))
            
            # Extract boundary from content-type
            content_type = request_data.get('headers', {}).get('content-type', '')
            if 'multipart/form-data' not in content_type:
                raise ValueError("Invalid content type. Expected multipart/form-data")
            
            # In a real implementation, you would parse the multipart form data here
            # For simplicity, we'll assume the API Gateway integration has been configured
            # to convert the multipart form to JSON
            
            # Create a temp file
            profile_path = os.path.join(tempfile.gettempdir(), f"profile_{uuid.uuid4()}.json")
            
            with open(profile_path, 'wb') as f:
                f.write(content)
            
            return None, profile_path
    
    # Standard Flask request with files
    elif 'profile' in request.files:
        profile_file = request.files['profile']
        
        # Check if file is empty
        if profile_file.filename == '':
            raise ValueError("No profile file selected")
        
        # Check if file is allowed
        if not allowed_file(profile_file.filename):
            raise ValueError("Invalid file type, only JSON files are allowed")
        
        # Generate unique filename
        unique_id = str(uuid.uuid4())
        filename = secure_filename(profile_file.filename)
        filename_parts = filename.rsplit('.', 1)
        unique_filename = f"{filename_parts[0]}_{unique_id}.{filename_parts[1]}"
        
        if IS_AWS and s3_client and ENV_S3_BUCKET:
            # Save to S3
            profile_path = f"uploads/{unique_filename}"
            save_file_to_s3(profile_file.read(), ENV_S3_BUCKET, profile_path)
            profile_path = f"s3://{ENV_S3_BUCKET}/{profile_path}"
        else:
            # Save to local file system
            profile_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            profile_file.save(profile_path)
        
        return unique_id, profile_path
    
    # Direct JSON data
    elif request.is_json:
        data = request.get_json()
        profile_data = data.get('profile', {})
        
        # Save profile data to temp file
        unique_id = str(uuid.uuid4())
        
        if IS_AWS and s3_client and ENV_S3_BUCKET:
            # Save to S3
            profile_path = f"uploads/temp_profile_{unique_id}.json"
            save_file_to_s3(json.dumps(profile_data).encode('utf-8'), ENV_S3_BUCKET, profile_path)
            profile_path = f"s3://{ENV_S3_BUCKET}/{profile_path}"
        else:
            # Save to local file system
            profile_path = os.path.join(app.config['UPLOAD_FOLDER'], f"temp_profile_{unique_id}.json")
            with open(profile_path, 'w', encoding='utf-8') as f:
                json.dump(profile_data, f, indent=2, ensure_ascii=False)
        
        return unique_id, profile_path
    
    else:
        raise ValueError("No profile data provided")


@app.route('/generate', methods=['POST'])
def generate_document():
    """
    Generate a document based on a delegate profile.
    
    Returns:
        JSON response with generation results
    """
    try:
        # Process file upload
        try:
            unique_id, profile_path = _process_file_upload(request.form if not IS_LAMBDA else request)
        except ValueError as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 400
        
        # Get parameters
        if IS_LAMBDA:
            # Parse JSON body for Lambda
            if request.is_json:
                params = request.get_json()
            else:
                # Try to parse form data from the event
                params = {}
                if 'body' in request and isinstance(request.get('body'), str):
                    try:
                        body_json = json.loads(request.get('body'))
                        if isinstance(body_json, dict):
                            params = body_json
                    except:
                        pass
        else:
            # Standard Flask request handling
            params = request.form
        
        # Get document type
        document_type = params.get('document_type', 'position_paper')
        if document_type not in ["position_paper", "speech", "resolution"]:
            return jsonify({
                'success': False,
                'error': 'Invalid document type. Must be one of: position_paper, speech, resolution'
            }), 400
        
        # Get common parameters
        topic = params.get('topic', None)
        committee = params.get('committee', None)
        country = params.get('country', None)
        
        # Get document-specific parameters
        additional_params = {}
        
        # Speech-specific parameters
        if document_type == "speech":
            speech_length = params.get('speech_length', None)
            occasion = params.get('occasion', None)
            is_opening = params.get('is_opening', 'true').lower() == 'true'
            
            if speech_length:
                additional_params["speech_length"] = speech_length
            if occasion:
                additional_params["occasion"] = occasion
            additional_params["is_opening"] = is_opening
        
        # Resolution-specific parameters
        elif document_type == "resolution":
            resolution_type = params.get('resolution_type', None)
            co_sponsors = params.get('co_sponsors', None)
            resolution_number = params.get('resolution_number', None)
            
            if resolution_type:
                additional_params["resolution_type"] = resolution_type
            if co_sponsors:
                if isinstance(co_sponsors, str):
                    additional_params["co_sponsors"] = [c.strip() for c in co_sponsors.split(",")]
                elif isinstance(co_sponsors, list):
                    additional_params["co_sponsors"] = co_sponsors
            if resolution_number:
                additional_params["resolution_number"] = resolution_number
        
        # Get generator instance
        generator = get_generator_instance()
        
        # Generate document
        output_path, document_data = generator.generate_document(
            delegate_profile_path=profile_path,
            document_type=document_type,
            topic=topic,
            committee=committee,
            country=country,
            additional_params=additional_params
        )
        
        # For S3 storage, copy the generated file to S3 if it's not already there
        if IS_AWS and s3_client and ENV_S3_BUCKET and not output_path.startswith('s3://'):
            s3_key = f"generated_documents/{os.path.basename(output_path)}"
            with open(output_path, 'rb') as f:
                save_file_to_s3(f.read(), ENV_S3_BUCKET, s3_key)
            
            # Update the output path
            output_path = f"s3://{ENV_S3_BUCKET}/{s3_key}"
        
        # Create response
        response = {
            'success': True,
            'profile_id': unique_id,
            'output_file': os.path.basename(output_path),
            'document_type': document_type,
            'metadata': document_data["metadata"],
            'generation_info': document_data["generation_info"]
        }
        
        # Add download URL for S3 storage
        if IS_AWS and s3_client and ENV_S3_BUCKET and output_path.startswith('s3://'):
            # Extract bucket and key from s3:// URL
            _, path = output_path.split('://', 1)
            bucket, key = path.split('/', 1)
            
            # Generate presigned URL
            download_url = generate_presigned_url(bucket, key)
            response['download_url'] = download_url
        
        # Format response for Lambda if needed
        if IS_LAMBDA:
            return {
                'statusCode': 200,
                'body': json.dumps(response),
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                }
            }
        
        return jsonify(response), 200
    
    except Exception as e:
        logger.error(f"Error generating document: {e}")
        error_details = {
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc() if ENV_TEST_MODE else None
        }
        
        # Format error response for Lambda if needed
        if IS_LAMBDA:
            return {
                'statusCode': 500,
                'body': json.dumps(error_details),
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                }
            }
        
        return jsonify(error_details), 500


@app.route('/generate-from-data', methods=['POST'])
def generate_from_data():
    """
    Generate a document from JSON data.
    
    Returns:
        JSON response with generation results
    """
    try:
        # Get JSON data
        if IS_LAMBDA:
            # For Lambda, body might be a string that needs to be parsed
            if 'body' in request and isinstance(request.get('body'), str):
                data = json.loads(request.get('body'))
            else:
                data = request
        else:
            # Standard Flask request
            data = request.json
        
        if not data:
            error_msg = 'No data provided'
            if IS_LAMBDA:
                return {
                    'statusCode': 400,
                    'body': json.dumps({
                        'success': False,
                        'error': error_msg
                    }),
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    }
                }
            return jsonify({'success': False, 'error': error_msg}), 400
        
        # Get document type
        document_type = data.get('document_type', 'position_paper')
        if document_type not in ["position_paper", "speech", "resolution"]:
            error_msg = 'Invalid document type. Must be one of: position_paper, speech, resolution'
            if IS_LAMBDA:
                return {
                    'statusCode': 400,
                    'body': json.dumps({
                        'success': False,
                        'error': error_msg
                    }),
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    }
                }
            return jsonify({'success': False, 'error': error_msg}), 400
        
        # Save profile data to a temporary file
        unique_id = str(uuid.uuid4())
        profile_data = data.get('profile', {})
        
        if IS_AWS and s3_client and ENV_S3_BUCKET:
            # Save to S3
            profile_s3_key = f"uploads/temp_profile_{unique_id}.json"
            save_file_to_s3(
                json.dumps(profile_data).encode('utf-8'),
                ENV_S3_BUCKET, 
                profile_s3_key
            )
            profile_path = f"s3://{ENV_S3_BUCKET}/{profile_s3_key}"
        else:
            # Save to local file system
            profile_path = os.path.join(app.config['UPLOAD_FOLDER'], f"temp_profile_{unique_id}.json")
            with open(profile_path, 'w', encoding='utf-8') as f:
                json.dump(profile_data, f, indent=2, ensure_ascii=False)
        
        # Get common parameters
        topic = data.get('topic', None)
        committee = data.get('committee', None)
        country = data.get('country', None)
        
        # Get document-specific parameters
        additional_params = data.get('additional_params', {})
        
        # Get generator instance
        generator = get_generator_instance()
        
        # Generate document
        output_path, document_data = generator.generate_document(
            delegate_profile_path=profile_path,
            document_type=document_type,
            topic=topic,
            committee=committee,
            country=country,
            additional_params=additional_params
        )
        
        # For S3 storage, copy the generated file to S3 if it's not already there
        if IS_AWS and s3_client and ENV_S3_BUCKET and not output_path.startswith('s3://'):
            s3_key = f"generated_documents/{os.path.basename(output_path)}"
            with open(output_path, 'rb') as f:
                save_file_to_s3(f.read(), ENV_S3_BUCKET, s3_key)
            
            # Update the output path
            s3_output_path = f"s3://{ENV_S3_BUCKET}/{s3_key}"
        else:
            s3_output_path = None
        
        # Clean up temporary file
        if not profile_path.startswith('s3://'):
            try:
                os.remove(profile_path)
            except Exception as e:
                logger.warning(f"Error removing temporary file: {e}")
        
        # Create response
        response = {
            'success': True,
            'output_file': os.path.basename(output_path),
            'document_type': document_type,
            'metadata': document_data["metadata"],
            'generation_info': document_data["generation_info"]
        }
        
        # Add download URL for S3 storage
        if IS_AWS and s3_client and ENV_S3_BUCKET and (output_path.startswith('s3://') or s3_output_path):
            # Extract bucket and key from s3:// URL
            s3_path = s3_output_path if s3_output_path else output_path
            _, path = s3_path.split('://', 1)
            bucket, key = path.split('/', 1)
            
            # Generate presigned URL
            download_url = generate_presigned_url(bucket, key)
            response['download_url'] = download_url
        
        # Format response for Lambda if needed
        if IS_LAMBDA:
            return {
                'statusCode': 200,
                'body': json.dumps(response),
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                }
            }
        
        return jsonify(response), 200
    
    except Exception as e:
        logger.error(f"Error generating document: {e}")
        error_details = {
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc() if ENV_TEST_MODE else None
        }
        
        # Format error response for Lambda if needed
        if IS_LAMBDA:
            return {
                'statusCode': 500,
                'body': json.dumps(error_details),
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                }
            }
        
        return jsonify(error_details), 500


@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    """
    Download a generated document.
    
    Args:
        filename: Name of the file to download
        
    Returns:
        File for download or redirect to presigned URL
    """
    try:
        if IS_AWS and s3_client and ENV_S3_BUCKET:
            # Generate presigned URL for S3 object
            s3_key = f"generated_documents/{filename}"
            
            # Check if file exists in S3
            try:
                s3_client.head_object(Bucket=ENV_S3_BUCKET, Key=s3_key)
            except ClientError as e:
                if e.response['Error']['Code'] == '404':
                    if IS_LAMBDA:
                        return {
                            'statusCode': 404,
                            'body': json.dumps({'error': 'File not found'}),
                            'headers': {
                                'Content-Type': 'application/json',
                                'Access-Control-Allow-Origin': '*'
                            }
                        }
                    return jsonify({'error': 'File not found'}), 404
                raise
            
            # Generate presigned URL
            url = generate_presigned_url(ENV_S3_BUCKET, s3_key)
            
            if IS_LAMBDA:
                return {
                    'statusCode': 302,  # Redirect
                    'headers': {
                        'Location': url,
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': ''
                }
            
            # Redirect to the presigned URL
            return Response(status=302, headers={'Location': url})
        else:
            # Local file system
            output_dir = config.GENERATOR_CONFIG.get("output_dir", "generated_documents")
            return send_from_directory(output_dir, filename, as_attachment=True)
    
    except Exception as e:
        logger.error(f"Error downloading file: {e}")
        error_msg = {'error': str(e)}
        
        if IS_LAMBDA:
            return {
                'statusCode': 500,
                'body': json.dumps(error_msg),
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                }
            }
        
        return jsonify(error_msg), 500


@app.route('/compare', methods=['POST'])
def compare_documents():
    """
    Compare an original document with a generated one.
    
    Returns:
        JSON response with comparison results
    """
    try:
        # Get JSON data
        if IS_LAMBDA:
            # For Lambda, body might be a string that needs to be parsed
            if 'body' in request and isinstance(request.get('body'), str):
                data = json.loads(request.get('body'))
            else:
                data = request
        else:
            data = request.form if request.form else request.json
        
        # Get paths to original and generated documents
        original_path = data.get('original_path')
        generated_path = data.get('generated_path')
        
        if not original_path or not generated_path:
            error_msg = 'Both original and generated document paths are required'
            if IS_LAMBDA:
                return {
                    'statusCode': 400,
                    'body': json.dumps({'success': False, 'error': error_msg}),
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    }
                }
            return jsonify({'success': False, 'error': error_msg}), 400
        
        # Load documents
        if IS_AWS and s3_client:
            # Check if paths are S3 paths
            original_data = load_document_from_path(original_path)
            generated_data = load_document_from_path(generated_path)
        else:
            # Local file paths
            with open(original_path, 'r', encoding='utf-8') as f:
                original_data = json.load(f)
            
            with open(generated_path, 'r', encoding='utf-8') as f:
                generated_data = json.load(f)
        
        # Compare documents based on their type
        document_type = generated_data["metadata"].get("document_type", "position_paper")
        
        # Basic comparison common to all document types
        comparison = {
            'metadata': {
                'original': {
                    'document_type': original_data["metadata"].get("document_type", "unknown"),
                    'committee': original_data["metadata"].get("committee"),
                    'country': original_data["metadata"].get("country"),
                    'topic': original_data["metadata"].get("main_topic")
                },
                'generated': {
                    'document_type': document_type,
                    'committee': generated_data["metadata"].get("committee"),
                    'country': generated_data["metadata"].get("country"),
                    'topic': generated_data["metadata"].get("main_topic")
                }
            },
            'statistics': {
                'original': {
                    'word_count': len(original_data["content"]["full_text"].split()),
                    'sentence_count': len(original_data["content"].get("sentences", [])),
                    'paragraph_count': len(original_data["content"].get("paragraphs", []))
                },
                'generated': {
                    'word_count': len(generated_data["content"]["full_text"].split()),
                    'sentence_count': len(generated_data["content"].get("sentences", [])),
                    'paragraph_count': len(generated_data["content"].get("paragraphs", []))
                }
            }
        }
        
        # Document-specific comparisons
        if document_type == "resolution":
            # Add resolution-specific comparison metrics
            comparison['resolution_metrics'] = {
                'original': {
                    'preambulatory_count': len(original_data["content"].get("structured_clauses", {}).get("preambulatory", [])),
                    'operative_count': len(original_data["content"].get("structured_clauses", {}).get("operative", []))
                },
                'generated': {
                    'preambulatory_count': len(generated_data["content"].get("structured_clauses", {}).get("preambulatory", [])),
                    'operative_count': len(generated_data["content"].get("structured_clauses", {}).get("operative", []))
                }
            }
        
        elif document_type == "speech":
            # Add speech-specific comparison metrics
            comparison['speech_metrics'] = {
                'original': {
                    'rhetorical_questions': sum(1 for s in original_data["content"].get("sentences", []) if s.endswith('?')),
                    'direct_address': sum(1 for p in original_data["content"].get("paragraphs", []) if "Chair" in p or "delegate" in p)
                },
                'generated': {
                    'rhetorical_questions': sum(1 for s in generated_data["content"].get("sentences", []) if s.endswith('?')),
                    'direct_address': sum(1 for p in generated_data["content"].get("paragraphs", []) if "Chair" in p or "delegate" in p)
                }
            }
        
        # Format response for Lambda if needed
        response = {'success': True, 'comparison': comparison}
        if IS_LAMBDA:
            return {
                'statusCode': 200,
                'body': json.dumps(response),
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                }
            }
        
        return jsonify(response), 200
    
    except Exception as e:
        logger.error(f"Error comparing documents: {e}")
        error_details = {
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc() if ENV_TEST_MODE else None
        }
        
        # Format error response for Lambda if needed
        if IS_LAMBDA:
            return {
                'statusCode': 500,
                'body': json.dumps(error_details),
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                }
            }
        
        return jsonify(error_details), 500

def load_document_from_path(path):
    """
    Load a document from a path (local or S3)
    
    Args:
        path: Path to the document
        
    Returns:
        Document data
    """
    if path.startswith('s3://'):
        # S3 path
        _, s3_path = path.split('://', 1)
        bucket, key = s3_path.split('/', 1)
        
        # Get document from S3
        content = get_file_from_s3(bucket, key)
        return json.loads(content.decode('utf-8'))
    else:
        # Local path
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

@app.route('/document-types', methods=['GET'])
def get_document_types():
    """
    Get available document types and their parameters.
    
    Returns:
        JSON response with document types
    """
    document_types = {
        'position_paper': {
            'description': 'A formal written document presenting a country\'s stance on an issue',
            'parameters': []
        },
        'speech': {
            'description': 'A formal speech delivered by a delegate',
            'parameters': [
                {
                    'name': 'speech_length',
                    'description': 'Length of the speech (e.g., "5-7 minutes")',
                    'required': False
                },
                {
                    'name': 'occasion',
                    'description': 'The occasion for the speech (e.g., "General Debate")',
                    'required': False
                },
                {
                    'name': 'is_opening',
                    'description': 'Whether this is an opening speech (true/false)',
                    'required': False
                }
            ]
        },
        'resolution': {
            'description': 'A formal UN resolution with preambulatory and operative clauses',
            'parameters': [
                {
                    'name': 'resolution_type',
                    'description': 'Type of resolution (e.g., "Draft Resolution")',
                    'required': False
                },
                {
                    'name': 'co_sponsors',
                    'description': 'Comma-separated list of co-sponsoring countries',
                    'required': False
                },
                {
                    'name': 'resolution_number',
                    'description': 'Resolution number if assigned',
                    'required': False
                }
            ]
        }
    }
    
    # Format response for Lambda if needed
    if IS_LAMBDA:
        return {
            'statusCode': 200,
            'body': json.dumps(document_types),
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            }
        }
    
    return jsonify(document_types), 200


@app.route('/health', methods=['GET'])
def health_check():
    """
    Check API health.
    
    Returns:
        JSON response with health status
    """
    health_data = {
        'status': 'healthy',
        'version': '1.0.0',
        'supported_document_types': ['position_paper', 'speech', 'resolution'],
        'environment': 'lambda' if IS_LAMBDA else 'container' if IS_AWS else 'local',
        'timestamp': time.time()
    }
    
    # Format response for Lambda if needed
    if IS_LAMBDA:
        return {
            'statusCode': 200,
            'body': json.dumps(health_data),
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            }
        }
    
    return jsonify(health_data), 200


# Lambda handler function
def lambda_handler(event, context):
    """
    AWS Lambda handler function
    
    Args:
        event: Lambda event
        context: Lambda context
        
    Returns:
        Lambda response
    """
    logger.info(f"Lambda event: {json.dumps(event)}")
    
    # Set request to the event
    global request
    request = event
    
    # If testing, set an environment variable and return a mock response
    if ENV_TEST_MODE:
        logger.info("Running in test mode, returning mock response")
        return {
            'statusCode': 200,
            'body': json.dumps({
                'status': 'test_success',
                'message': 'This is a test response',
                'event': event
            }),
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            }
        }
    
    # Process using Flask app
    with app.test_request_context(
        path=event.get('path', '/'),
        method=event.get('httpMethod', 'GET'),
        headers=event.get('headers', {}),
        data=event.get('body', '{}')
    ):
        # Get the function for the route
        endpoint = app.view_functions.get(request.endpoint)
        if not endpoint:
            return {
                'statusCode': 404,
                'body': json.dumps({'error': 'Route not found'}),
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                }
            }
        
        # Call the endpoint function
        return endpoint()


# Enable CORS for API Gateway
def enable_cors(response):
    """
    Enable CORS for API Gateway response.
    
    Args:
        response: API response
        
    Returns:
        Response with CORS headers
    """
    if not isinstance(response, dict):
        return response
    
    # Add CORS headers if not present
    if 'headers' not in response:
        response['headers'] = {}
    
    response['headers']['Access-Control-Allow-Origin'] = '*'
    response['headers']['Access-Control-Allow-Headers'] = 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'
    response['headers']['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS'
    
    return response


# Create test client setup for testing
def create_test_client():
    """
    Create a test client for the Flask app
    
    Returns:
        Flask test client
    """
    # Set test mode
    os.environ["TEST_ENV"] = "true"
    
    # Create test app
    test_app = Flask(__name__)
    test_app.config.update(app.config)
    
    # Copy all routes from main app
    for rule in app.url_map.iter_rules():
        endpoint = app.view_functions[rule.endpoint]
        test_app.add_url_rule(rule.rule, rule.endpoint, endpoint, methods=rule.methods)
    
    # Return test client
    return test_app.test_client()


# Run the app for local development
if __name__ == '__main__':
    app.run(
        host=config.API_CONFIG.get("host", "0.0.0.0"),
        port=config.API_CONFIG.get("port", 5001),
        debug=config.API_CONFIG.get("debug", False)
    )
