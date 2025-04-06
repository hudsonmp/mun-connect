#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Configuration Module

This module contains configuration settings for the document processing pipeline.
Supports both local filesystem and AWS S3 storage with testing environment options.
Includes AWS Lambda and service discovery configurations for production deployments.
"""

import os
import json
import logging
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, Union, BinaryIO, TypeVar, List
from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError

# Configure logging
logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Import boto3 for AWS operations
try:
    import boto3
    from boto3.session import Session
    AWS_AVAILABLE = True
except ImportError:
    AWS_AVAILABLE = False
    logger.warning("boto3 not installed. AWS functionality will not be available.")

# ======= Environment Detection =======
ENV_STAGE = os.environ.get("DEPLOYMENT_STAGE", "dev").lower()
ENV_TEST_MODE = os.environ.get("TEST_ENV", "false").lower() == "true"
IS_LAMBDA = os.environ.get("AWS_LAMBDA_FUNCTION_NAME") is not None
IS_PRODUCTION = ENV_STAGE in ["prod", "production"]

# ======= Storage Configuration =======
ENV_STORAGE_MODE = os.environ.get("STORAGE_MODE", "local" if ENV_TEST_MODE else "s3").lower()

# ======= Path Configuration =======
# Use environment variable for base directory if provided, otherwise use local path
ENV_BASE_DIR = os.environ.get("PDF_TRANSFORM_BASE_DIR")
BASE_DIR = Path(ENV_BASE_DIR) if ENV_BASE_DIR else Path(__file__).resolve().parent

# Directories are determined by environment variables or defaults
ENV_OUTPUT_DIR = os.environ.get("PDF_TRANSFORM_OUTPUT_DIR")
ENV_TEMP_DIR = os.environ.get("PDF_TRANSFORM_TEMP_DIR")
ENV_UPLOADS_DIR = os.environ.get("PDF_TRANSFORM_UPLOADS_DIR")

# Set directory paths based on environment variables or defaults
OUTPUT_DIR = ENV_OUTPUT_DIR or os.path.join(BASE_DIR, "output")
TEMP_DIR = ENV_TEMP_DIR or os.path.join(BASE_DIR, "temp")
UPLOADS_DIR = ENV_UPLOADS_DIR or os.path.join(BASE_DIR, "uploads")

# ======= AWS Configuration =======
# S3 Configuration
ENV_S3_BUCKET = os.environ.get("PDF_TRANSFORM_S3_BUCKET")
ENV_S3_REGION = os.environ.get("PDF_TRANSFORM_S3_REGION", "us-east-1")
ENV_S3_OUTPUT_PREFIX = os.environ.get("PDF_TRANSFORM_S3_OUTPUT_PREFIX", "processed/")
ENV_S3_UPLOAD_PREFIX = os.environ.get("PDF_TRANSFORM_S3_UPLOAD_PREFIX", "uploads/")

# Lambda Function References
ENV_LAMBDA_REGION = os.environ.get("PDF_TRANSFORM_LAMBDA_REGION", ENV_S3_REGION)
ENV_LAMBDA_PROCESSOR_ARN = os.environ.get("PDF_TRANSFORM_PROCESSOR_LAMBDA_ARN")
ENV_LAMBDA_ANALYZER_ARN = os.environ.get("PDF_TRANSFORM_ANALYZER_LAMBDA_ARN")

# AWS Service Discovery
ENV_SERVICE_DISCOVERY_NAMESPACE = os.environ.get("SERVICE_DISCOVERY_NAMESPACE")
ENV_SERVICE_NAME = os.environ.get("SERVICE_NAME", "pdf-transform")

# AWS Systems Manager Parameter Store
ENV_PARAMETER_STORE_PREFIX = os.environ.get("PARAMETER_STORE_PREFIX", f"/{ENV_STAGE}/pdf-transform/")

# IAM Role Configuration
ENV_IAM_ROLE_ARN = os.environ.get("PDF_TRANSFORM_IAM_ROLE_ARN")
IAM_REQUIRED_PERMISSIONS = [
    "s3:GetObject",
    "s3:PutObject",
    "s3:ListBucket",
    "lambda:InvokeFunction",
    "servicediscovery:DiscoverInstances",
    "ssm:GetParameter",
    "ssm:GetParameters",
    "ssm:GetParametersByPath",
    "logs:CreateLogGroup",
    "logs:CreateLogStream",
    "logs:PutLogEvents"
]

# ======= Feature Configuration =======
# Models configuration - Allow overriding with environment variables
MODELS = {
    "bert": {
        "default": os.environ.get("PDF_TRANSFORM_BERT_MODEL", "bert-base-uncased"),
        "large": os.environ.get("PDF_TRANSFORM_BERT_LARGE_MODEL", "bert-large-uncased"),
        "multilingual": os.environ.get("PDF_TRANSFORM_BERT_MULTILINGUAL_MODEL", "bert-base-multilingual-cased")
    },
    "argument_component": {
        "default": os.environ.get("PDF_TRANSFORM_ARG_COMPONENT_MODEL", "mtei/distilroberta-argument-component-detection")
    },
    "argument_relation": {
        "default": os.environ.get("PDF_TRANSFORM_ARG_RELATION_MODEL", "mtei/bert-base-argument-relation-classification")
    },
    "reasoning": {
        "default": os.environ.get("PDF_TRANSFORM_REASONING_MODEL", "distilbert-base-uncased-finetuned-mnli")
    }
}

# Processing options - Allow overriding with environment variables
PROCESSING_OPTIONS = {
    "use_markdown": os.environ.get("PDF_TRANSFORM_USE_MARKDOWN", "true").lower() == "true",
    "use_spacy": os.environ.get("PDF_TRANSFORM_USE_SPACY", "true").lower() == "true",
    "use_transformers": os.environ.get("PDF_TRANSFORM_USE_TRANSFORMERS", "true").lower() == "true",
    "parallel_processing": os.environ.get("PDF_TRANSFORM_PARALLEL", "false").lower() == "true",
    "use_gpu": os.environ.get("PDF_TRANSFORM_USE_GPU", "false").lower() == "true",
    "max_workers": int(os.environ.get("PDF_TRANSFORM_MAX_WORKERS", "4"))
}

# ======= API Configuration =======
# Flask API configuration with environment variable overrides
API_CONFIG = {
    "host": os.environ.get("PDF_TRANSFORM_API_HOST", "0.0.0.0"),
    "port": int(os.environ.get("PDF_TRANSFORM_API_PORT", "5000")),
    "debug": os.environ.get("PDF_TRANSFORM_API_DEBUG", "false").lower() == "true",
    "upload_folder": UPLOADS_DIR,
    "allowed_extensions": set(os.environ.get("PDF_TRANSFORM_ALLOWED_EXTENSIONS", "pdf").split(",")),
    "max_content_length": int(os.environ.get("PDF_TRANSFORM_MAX_CONTENT_LENGTH", "16777216"))  # 16MB default
}

# ======= S3 Configuration =======
S3_CONFIG = {
    "bucket": ENV_S3_BUCKET,
    "region": ENV_S3_REGION,
    "output_prefix": ENV_S3_OUTPUT_PREFIX,
    "upload_prefix": ENV_S3_UPLOAD_PREFIX,
    "presigned_url_expiry": int(os.environ.get("PDF_TRANSFORM_PRESIGNED_URL_EXPIRY", "3600"))  # 1 hour default
}

# ======= Test Configuration =======
TEST_CONFIG = {
    "mock_s3": ENV_TEST_MODE,
    "mock_lambda": ENV_TEST_MODE,
    "mock_ssm": ENV_TEST_MODE,
    "mock_service_discovery": ENV_TEST_MODE,
    "test_s3_bucket": os.environ.get("PDF_TRANSFORM_TEST_S3_BUCKET", "test-pdf-transform-bucket"),
    "test_data_dir": os.environ.get("PDF_TRANSFORM_TEST_DATA_DIR", os.path.join(BASE_DIR, "test_data")),
    "test_output_dir": os.environ.get("PDF_TRANSFORM_TEST_OUTPUT_DIR", os.path.join(BASE_DIR, "test_output"))
}

# Type variable for generic return
T = TypeVar('T')

class ConfigHandler:
    """Handles configuration and storage operations for both local and AWS environments."""
    
    def __init__(self, use_s3: Optional[bool] = None):
        """Initialize the config handler with the appropriate storage mode.
        
        Args:
            use_s3: Override environment settings and explicitly use S3 or local storage
        """
        # Determine storage mode
        if use_s3 is not None:
            self.use_s3 = use_s3
        elif ENV_TEST_MODE and not os.environ.get("FORCE_S3_IN_TEST", "false").lower() == "true":
            self.use_s3 = False
            logger.info("Test mode detected, using local storage")
        else:
            self.use_s3 = ENV_STORAGE_MODE == "s3"
            
        # Initialize AWS service clients
        self.s3_client = None
        self.lambda_client = None
        self.ssm_client = None
        self.service_discovery_client = None
        
        # Set up AWS clients if needed
        if self.use_s3 or IS_LAMBDA or IS_PRODUCTION:
            if not AWS_AVAILABLE:
                raise ImportError("boto3 is required for AWS operations")
            
            # Create a session with the specified region
            self.aws_session = boto3.session.Session(region_name=ENV_S3_REGION)
            
            # Initialize S3 client
            if self.use_s3:
                if not S3_CONFIG["bucket"]:
                    raise ValueError("S3 bucket name must be provided through PDF_TRANSFORM_S3_BUCKET environment variable")
                
                try:
                    self.s3_client = self.aws_session.client('s3')
                    # Verify IAM permissions by checking if we can list the bucket
                    self.s3_client.head_bucket(Bucket=S3_CONFIG["bucket"])
                    logger.info(f"Successfully connected to S3 bucket: {S3_CONFIG['bucket']}")
                except (ClientError, NoCredentialsError, PartialCredentialsError) as e:
                    if isinstance(e, ClientError) and e.response['Error']['Code'] == '403':
                        logger.error(f"Permission denied to access S3 bucket: {S3_CONFIG['bucket']}")
                        logger.error("Required IAM permissions: s3:GetObject, s3:PutObject, s3:ListBucket")
                    else:
                        logger.error(f"Failed to initialize S3 client: {str(e)}")
                    raise
            
            # Initialize Lambda client if we have Lambda ARNs configured
            if ENV_LAMBDA_PROCESSOR_ARN or ENV_LAMBDA_ANALYZER_ARN:
                try:
                    self.lambda_client = self.aws_session.client('lambda', region_name=ENV_LAMBDA_REGION)
                    logger.info("Successfully initialized Lambda client")
                except (ClientError, NoCredentialsError, PartialCredentialsError) as e:
                    logger.error(f"Failed to initialize Lambda client: {str(e)}")
                    logger.error("Required IAM permission: lambda:InvokeFunction")
                    # Non-fatal error for Lambda client, continue without it
            
            # Initialize SSM client for parameter store access
            try:
                self.ssm_client = self.aws_session.client('ssm')
                logger.info("Successfully initialized SSM client for parameter store")
            except (ClientError, NoCredentialsError, PartialCredentialsError) as e:
                logger.error(f"Failed to initialize SSM client: {str(e)}")
                logger.error("Required IAM permissions: ssm:GetParameter, ssm:GetParameters, ssm:GetParametersByPath")
                # Non-fatal error for SSM client, continue without it
            
            # Initialize Service Discovery client if namespace is configured
            if ENV_SERVICE_DISCOVERY_NAMESPACE:
                try:
                    self.service_discovery_client = self.aws_session.client('servicediscovery')
                    logger.info(f"Successfully initialized Service Discovery client for namespace: {ENV_SERVICE_DISCOVERY_NAMESPACE}")
                except (ClientError, NoCredentialsError, PartialCredentialsError) as e:
                    logger.error(f"Failed to initialize Service Discovery client: {str(e)}")
                    logger.error("Required IAM permission: servicediscovery:DiscoverInstances")
                    # Non-fatal error for Service Discovery client, continue without it
            
        # Set up directory structure for local or test mode
        if not self.use_s3:
            # Create local directories
            if ENV_TEST_MODE:
                # Use temporary directories for testing
                self.temp_dir = tempfile.TemporaryDirectory()
                self.test_output_dir = os.path.join(self.temp_dir.name, "output")
                self.test_upload_dir = os.path.join(self.temp_dir.name, "uploads")
                os.makedirs(self.test_output_dir, exist_ok=True)
                os.makedirs(self.test_upload_dir, exist_ok=True)
                logger.info(f"Using temporary directory for testing: {self.temp_dir.name}")
            else:
                # Create required directories for local mode
                os.makedirs(OUTPUT_DIR, exist_ok=True)
                os.makedirs(UPLOADS_DIR, exist_ok=True)
                os.makedirs(TEMP_DIR, exist_ok=True)
                logger.info(f"Using local storage with output directory: {OUTPUT_DIR}")
    
    def get_service_endpoint(self, service_name: Optional[str] = None) -> Optional[str]:
        """Discover service endpoint using AWS Service Discovery.
        
        Args:
            service_name: Name of the service to discover, defaults to ENV_SERVICE_NAME
            
        Returns:
            Service endpoint URL or None if not found
        """
        if not self.service_discovery_client or not ENV_SERVICE_DISCOVERY_NAMESPACE:
            return None
            
        service = service_name or ENV_SERVICE_NAME
        
        try:
            response = self.service_discovery_client.discover_instances(
                NamespaceName=ENV_SERVICE_DISCOVERY_NAMESPACE,
                ServiceName=service
            )
            
            if response['Instances']:
                instance = response['Instances'][0]  # Use the first instance
                protocol = instance.get('Attributes', {}).get('PROTOCOL', 'https')
                ip_address = instance.get('Attributes', {}).get('AWS_INSTANCE_IPV4')
                port = instance.get('Attributes', {}).get('AWS_INSTANCE_PORT')
                
                if ip_address and port:
                    return f"{protocol}://{ip_address}:{port}"
                    
            logger.warning(f"No instances found for service {service}")
            return None
            
        except ClientError as e:
            logger.error(f"Error discovering service {service}: {str(e)}")
            return None
    
    def get_parameter(self, param_name: str, decrypt: bool = False) -> Optional[str]:
        """Get a parameter from AWS Systems Manager Parameter Store.
        
        Args:
            param_name: Name of the parameter
            decrypt: Whether to decrypt the parameter value
            
        Returns:
            Parameter value or None if not found
        """
        if not self.ssm_client:
            if ENV_TEST_MODE:
                # Return mock values for testing
                if param_name.endswith("api_key"):
                    return "test-api-key-12345"
                elif param_name.endswith("secret"):
                    return "test-secret-value"
                else:
                    return f"test-param-value-for-{param_name}"
            return None
            
        # Add prefix if param_name doesn't start with /
        full_param_name = param_name if param_name.startswith('/') else f"{ENV_PARAMETER_STORE_PREFIX}{param_name}"
        
        try:
            response = self.ssm_client.get_parameter(
                Name=full_param_name,
                WithDecryption=decrypt
            )
            return response['Parameter']['Value']
        except ClientError as e:
            logger.error(f"Error getting parameter {full_param_name}: {str(e)}")
            return None
    
    def invoke_lambda(self, function_name: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Invoke an AWS Lambda function.
        
        Args:
            function_name: Name or ARN of the Lambda function
            payload: JSON payload to send to the function
            
        Returns:
            Lambda function response or None if invocation failed
        """
        if not self.lambda_client:
            if ENV_TEST_MODE and TEST_CONFIG["mock_lambda"]:
                logger.info(f"Mock Lambda invocation for {function_name}")
                # Return mock response for testing
                return {
                    "statusCode": 200,
                    "body": json.dumps({
                        "message": f"Mock response from {function_name}",
                        "input": payload
                    })
                }
            logger.error("Lambda client not initialized")
            return None
            
        try:
            response = self.lambda_client.invoke(
                FunctionName=function_name,
                InvocationType='RequestResponse',
                Payload=json.dumps(payload)
            )
            
            if response['StatusCode'] == 200:
                return json.loads(response['Payload'].read().decode('utf-8'))
            else:
                logger.error(f"Lambda invocation error: {response}")
                return None
                
        except ClientError as e:
            logger.error(f"Error invoking Lambda {function_name}: {str(e)}")
            return None
    
    def get_s3_presigned_url(self, key: str, expires_in: int = S3_CONFIG["presigned_url_expiry"], 
                            method: str = 'get_object') -> Optional[str]:
        """Generate a pre-signed URL for S3 object access.
        
        Args:
            key: S3 object key
            expires_in: URL expiration time in seconds
            method: S3 method ('get_object' or 'put_object')
            
        Returns:
            Pre-signed URL or None if generation failed
        """
        if not self.s3_client:
            return None
            
        try:
            url = self.s3_client.generate_presigned_url(
                ClientMethod=method,
                Params={
                    'Bucket': S3_CONFIG['bucket'],
                    'Key': key
                },
                ExpiresIn=expires_in
            )
            return url
        except ClientError as e:
            logger.error(f"Error generating presigned URL for {key}: {str(e)}")
            return None
    
    def open(self, path: str, mode: str = 'r') -> BinaryIO:
        """Open a file from either local storage or S3.
        
        Args:
            path: Path to the file
            mode: File open mode ('r', 'w', 'rb', 'wb')
        
        Returns:
            File-like object
        """
        if self.use_s3:
            if 'r' in mode:
                try:
                    s3_obj = self.s3_client.get_object(Bucket=S3_CONFIG["bucket"], Key=path)
                    return s3_obj['Body']
                except ClientError as e:
                    logger.error(f"Error reading file from S3: {str(e)}")
                    raise
            else:
                # For writing, return a temporary file that will be uploaded on close
                temp_file = tempfile.NamedTemporaryFile(mode=mode if 'b' in mode else f"{mode}b", delete=False)
                temp_file.s3_path = path  # Store S3 path for upload on close
                return temp_file
        else:
            # For local or test environment
            if ENV_TEST_MODE:
                # Use temporary directory for testing
                file_path = os.path.join(self.temp_dir.name, os.path.basename(path))
            else:
                file_path = path
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            return open(file_path, mode)
    
    def save(self, content: Union[str, bytes], path: str, is_binary: bool = False) -> None:
        """Save content to a file, either locally or to S3.
        
        Args:
            content: Content to save
            path: Path to save to
            is_binary: Whether the content is binary
        """
        if self.use_s3:
            try:
                self.s3_client.put_object(
                    Bucket=S3_CONFIG["bucket"],
                    Key=path,
                    Body=content if is_binary else content.encode('utf-8')
                )
            except ClientError as e:
                logger.error(f"Error saving file to S3: {str(e)}")
                raise
        else:
            # For local or test environment
            if ENV_TEST_MODE:
                file_path = os.path.join(self.temp_dir.name, os.path.basename(path))
            else:
                file_path = path
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Write content
            mode = 'wb' if is_binary else 'w'
            with open(file_path, mode) as f:
                f.write(content)
    
    def load(self, path: str, as_json: bool = False, binary: bool = False) -> T:
        """Load content from a file, either locally or from S3.
        
        Args:
            path: Path to load from
            as_json: Whether to parse the content as JSON
            binary: Whether to return binary content
        
        Returns:
            File content as string, bytes, or parsed JSON
        """
        if self.use_s3:
            try:
                s3_obj = self.s3_client.get_object(Bucket=S3_CONFIG["bucket"], Key=path)
                content = s3_obj['Body'].read()
                
                if binary:
                    return content
                
                content = content.decode('utf-8')
                return json.loads(content) if as_json else content
            except ClientError as e:
                logger.error(f"Error loading file from S3: {str(e)}")
                raise
        else:
            # For local or test environment
            if ENV_TEST_MODE:
                file_path = os.path.join(self.temp_dir.name, os.path.basename(path))
            else:
                file_path = path
            
            # Read content
            mode = 'rb' if binary else 'r'
            with open(file_path, mode) as f:
                content = f.read()
                
            if binary:
                return content
            
            return json.loads(content) if as_json else content
    
    def exists(self, path: str) -> bool:
        """Check if a file exists, either locally or in S3.
        
        Args:
            path: Path to check
            
        Returns:
            True if the file exists, False otherwise
        """
        if self.use_s3:
            try:
                self.s3_client.head_object(Bucket=S3_CONFIG["bucket"], Key=path)
                return True
            except ClientError as e:
                if e.response['Error']['Code'] == '404':
                    return False
                else:
                    logger.error(f"Error checking if file exists in S3: {str(e)}")
                    raise
        else:
            # For local or test environment
            if ENV_TEST_MODE:
                file_path = os.path.join(self.temp_dir.name, os.path.basename(path))
            else:
                file_path = path
            
            return os.path.exists(file_path)
    
    def __del__(self):
        """Clean up any resources when object is deleted."""
        if hasattr(self, 'temp_dir') and self.temp_dir:
            self.temp_dir.cleanup()

# Initialize a default config handler based on environment settings
config_handler = ConfigHandler()
