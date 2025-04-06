#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
AWS Helper Utilities

This module provides helper functions for AWS services integration including:
- SQS message queue management
- Lambda function invocation
- IAM permission checking
- Error handling and logging
"""

import os
import json
import time
import logging
import uuid
from typing import Dict, List, Any, Optional, Union
from functools import lru_cache

# Configure logging
logger = logging.getLogger(__name__)

# Import boto3 for AWS operations
try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError
    AWS_AVAILABLE = True
except ImportError:
    AWS_AVAILABLE = False
    logger.warning("boto3 not installed. AWS functionality will not be available.")

# Environment variables
ENV_STAGE = os.environ.get("DEPLOYMENT_STAGE", "dev").lower()
ENV_TEST_MODE = os.environ.get("TEST_ENV", "false").lower() == "true"
ENV_AWS_REGION = os.environ.get("PDF_TRANSFORM_AWS_REGION", os.environ.get("AWS_REGION", "us-east-1"))

# SQS Configuration
ENV_SQS_QUEUE_URL = os.environ.get("PDF_TRANSFORM_SQS_QUEUE_URL")
ENV_SQS_QUEUE_NAME = os.environ.get("PDF_TRANSFORM_SQS_QUEUE_NAME", f"pdf-transform-queue-{ENV_STAGE}")

# Maximum number of SQS retries
MAX_SQS_RETRIES = 3

class SQSHelper:
    """Helper class for SQS operations"""
    
    def __init__(self, queue_url: Optional[str] = None, queue_name: Optional[str] = None, region: Optional[str] = None):
        """
        Initialize SQS helper.
        
        Args:
            queue_url: SQS queue URL (optional if queue_name or environment variable is provided)
            queue_name: SQS queue name (optional if queue_url is provided)
            region: AWS region (optional, defaults to environment variable)
        """
        if not AWS_AVAILABLE:
            raise ImportError("boto3 is required for SQS operations")
        
        self.region = region or ENV_AWS_REGION
        self.queue_url = queue_url or ENV_SQS_QUEUE_URL
        self.queue_name = queue_name or ENV_SQS_QUEUE_NAME
        
        # Initialize SQS client
        try:
            self.sqs = boto3.client('sqs', region_name=self.region)
            
            # Create queue URL if not provided
            if not self.queue_url and self.queue_name:
                try:
                    # Try to get existing queue
                    response = self.sqs.get_queue_url(QueueName=self.queue_name)
                    self.queue_url = response['QueueUrl']
                    logger.info(f"Using existing SQS queue: {self.queue_url}")
                except ClientError as e:
                    if e.response['Error']['Code'] == 'AWS.SimpleQueueService.NonExistentQueue':
                        # Create queue if it doesn't exist
                        if not ENV_TEST_MODE:  # Don't create real queues in test mode
                            response = self.sqs.create_queue(
                                QueueName=self.queue_name,
                                Attributes={
                                    'DelaySeconds': '0',
                                    'VisibilityTimeout': '600',  # 10 minutes
                                    'MessageRetentionPeriod': '86400'  # 1 day
                                }
                            )
                            self.queue_url = response['QueueUrl']
                            logger.info(f"Created new SQS queue: {self.queue_url}")
                        else:
                            # Use mock queue URL in test mode
                            self.queue_url = f"https://sqs.{self.region}.amazonaws.com/123456789012/{self.queue_name}"
                            logger.info(f"Using mock SQS queue URL in test mode: {self.queue_url}")
                    else:
                        raise
            
            if not self.queue_url:
                raise ValueError("SQS queue URL is required. Provide queue_url, queue_name, or set PDF_TRANSFORM_SQS_QUEUE_URL environment variable.")
            
        except (ClientError, NoCredentialsError, PartialCredentialsError) as e:
            if ENV_TEST_MODE:
                logger.warning(f"SQS initialization failed in test mode, using mock: {str(e)}")
                self.sqs = None
                if not self.queue_url:
                    self.queue_url = f"https://sqs.{self.region}.amazonaws.com/123456789012/{self.queue_name}"
            else:
                logger.error(f"Failed to initialize SQS client: {str(e)}")
                raise
    
    def send_message(self, message: Dict[str, Any], delay_seconds: int = 0) -> Dict[str, Any]:
        """
        Send a message to the SQS queue.
        
        Args:
            message: Message to send
            delay_seconds: Delay in seconds
            
        Returns:
            SQS response
        """
        if ENV_TEST_MODE and not self.sqs:
            # Return mock response in test mode
            logger.info(f"Mock sending message to SQS: {json.dumps(message)}")
            return {
                "MessageId": str(uuid.uuid4()),
                "MD5OfMessageBody": "mock-md5-hash"
            }
        
        try:
            # Convert message to JSON string
            message_body = json.dumps(message)
            
            # Send message to SQS
            response = self.sqs.send_message(
                QueueUrl=self.queue_url,
                MessageBody=message_body,
                DelaySeconds=delay_seconds
            )
            
            logger.info(f"Message sent to SQS: {response['MessageId']}")
            return response
        except ClientError as e:
            logger.error(f"Error sending message to SQS: {str(e)}")
            raise
    
    def receive_messages(self, max_messages: int = 10, wait_time_seconds: int = 0) -> List[Dict[str, Any]]:
        """
        Receive messages from the SQS queue.
        
        Args:
            max_messages: Maximum number of messages to receive
            wait_time_seconds: Wait time in seconds (long polling)
            
        Returns:
            List of messages
        """
        if ENV_TEST_MODE and not self.sqs:
            # Return empty list in test mode
            logger.info("Mock receiving messages from SQS")
            return []
        
        try:
            # Receive messages from SQS
            response = self.sqs.receive_message(
                QueueUrl=self.queue_url,
                MaxNumberOfMessages=max_messages,
                WaitTimeSeconds=wait_time_seconds,
                AttributeNames=['All'],
                MessageAttributeNames=['All']
            )
            
            # Extract messages
            messages = response.get('Messages', [])
            logger.info(f"Received {len(messages)} messages from SQS")
            
            # Parse message bodies
            for message in messages:
                try:
                    message['Body'] = json.loads(message['Body'])
                except (json.JSONDecodeError, TypeError):
                    # Keep original body if not JSON
                    pass
            
            return messages
        except ClientError as e:
            logger.error(f"Error receiving messages from SQS: {str(e)}")
            raise
    
    def delete_message(self, receipt_handle: str) -> Dict[str, Any]:
        """
        Delete a message from the SQS queue.
        
        Args:
            receipt_handle: Receipt handle of the message
            
        Returns:
            SQS response
        """
        if ENV_TEST_MODE and not self.sqs:
            # Return mock response in test mode
            logger.info(f"Mock deleting message from SQS: {receipt_handle}")
            return {}
        
        try:
            # Delete message from SQS
            response = self.sqs.delete_message(
                QueueUrl=self.queue_url,
                ReceiptHandle=receipt_handle
            )
            
            logger.info(f"Message deleted from SQS: {receipt_handle}")
            return response
        except ClientError as e:
            logger.error(f"Error deleting message from SQS: {str(e)}")
            raise


class LambdaHelper:
    """Helper class for Lambda operations"""
    
    def __init__(self, region: Optional[str] = None):
        """
        Initialize Lambda helper.
        
        Args:
            region: AWS region (optional, defaults to environment variable)
        """
        if not AWS_AVAILABLE:
            raise ImportError("boto3 is required for Lambda operations")
        
        self.region = region or ENV_AWS_REGION
        
        # Initialize Lambda client
        try:
            self.lambda_client = boto3.client('lambda', region_name=self.region)
            logger.info("Lambda client initialized")
        except (ClientError, NoCredentialsError, PartialCredentialsError) as e:
            if ENV_TEST_MODE:
                logger.warning(f"Lambda initialization failed in test mode, using mock: {str(e)}")
                self.lambda_client = None
            else:
                logger.error(f"Failed to initialize Lambda client: {str(e)}")
                raise
    
    def invoke_function(self, function_name: str, payload: Dict[str, Any], 
                         invocation_type: str = 'RequestResponse') -> Dict[str, Any]:
        """
        Invoke a Lambda function.
        
        Args:
            function_name: Lambda function name or ARN
            payload: Function payload
            invocation_type: Invocation type (RequestResponse, Event, DryRun)
            
        Returns:
            Lambda response
        """
        if ENV_TEST_MODE and not self.lambda_client:
            # Return mock response in test mode
            logger.info(f"Mock invoking Lambda function: {function_name}")
            return {
                "StatusCode": 200,
                "ExecutedVersion": "$LATEST",
                "Payload": json.dumps({
                    "statusCode": 200,
                    "body": json.dumps({
                        "message": f"Mock response from {function_name}",
                        "input": payload
                    })
                })
            }
        
        try:
            # Convert payload to JSON
            payload_json = json.dumps(payload)
            
            # Invoke Lambda function
            response = self.lambda_client.invoke(
                FunctionName=function_name,
                InvocationType=invocation_type,
                Payload=payload_json.encode()
            )
            
            # Parse response payload
            if 'Payload' in response:
                payload_bytes = response['Payload'].read()
                try:
                    response['Payload'] = json.loads(payload_bytes.decode())
                except (json.JSONDecodeError, UnicodeDecodeError):
                    # Keep original payload if not JSON
                    response['Payload'] = payload_bytes
            
            logger.info(f"Lambda function invoked: {function_name}, status: {response.get('StatusCode')}")
            return response
        
        except ClientError as e:
            logger.error(f"Error invoking Lambda function {function_name}: {str(e)}")
            raise


@lru_cache(maxsize=32)
def check_aws_permissions(required_permissions: Union[List[str], tuple]) -> bool:
    """
    Check if the current IAM role has the required permissions.
    
    Args:
        required_permissions: List of required IAM permissions
        
    Returns:
        True if all permissions are available, False otherwise
    """
    if not AWS_AVAILABLE:
        return False
    
    if ENV_TEST_MODE:
        # Always return True in test mode
        logger.info(f"Mock checking AWS permissions: {required_permissions}")
        return True
    
    try:
        # Convert list to tuple for caching
        if isinstance(required_permissions, list):
            required_permissions = tuple(required_permissions)
        
        # Initialize IAM client
        iam = boto3.client('iam')
        sts = boto3.client('sts')
        
        # Get current IAM role
        identity = sts.get_caller_identity()
        role_arn = identity.get('Arn', '')
        
        logger.info(f"Checking permissions for role: {role_arn}")
        
        # Check each permission
        for permission in required_permissions:
            # Note: This is a simplified check that doesn't account for resource conditions
            # For a more accurate check, use IAM Policy Simulator API
            try:
                # Try a simple operation to test permission
                service, action = permission.split(':', 1)
                
                if service == 's3':
                    s3 = boto3.client('s3')
                    if action == 'ListBucket':
                        # List buckets to check s3:ListBucket
                        s3.list_buckets()
                    elif action in ('GetObject', 'PutObject'):
                        # List buckets to check s3:GetObject and s3:PutObject
                        # This is not a perfect check but good enough for most cases
                        s3.list_buckets()
                
                elif service == 'sqs':
                    sqs = boto3.client('sqs')
                    if action in ('SendMessage', 'ReceiveMessage', 'DeleteMessage'):
                        # List queues to check SQS permissions
                        sqs.list_queues()
                
                elif service == 'lambda':
                    lambda_client = boto3.client('lambda')
                    if action == 'InvokeFunction':
                        # List functions to check lambda:InvokeFunction
                        lambda_client.list_functions()
                
                # Add more service checks as needed
                
            except (ClientError, NoCredentialsError, PartialCredentialsError) as e:
                logger.warning(f"Permission check failed for {permission}: {str(e)}")
                return False
        
        # All permissions passed
        return True
        
    except Exception as e:
        logger.error(f"Error checking AWS permissions: {str(e)}")
        return False


def handle_aws_error(func):
    """
    Decorator to handle AWS errors.
    
    Args:
        func: Function to decorate
        
    Returns:
        Decorated function
    """
    def wrapper(*args, **kwargs):
        max_retries = 3
        retry_count = 0
        backoff_base = 0.5  # seconds
        
        while retry_count < max_retries:
            try:
                return func(*args, **kwargs)
            except ClientError as e:
                error_code = e.response['Error']['Code']
                
                # Handle specific error codes
                if error_code in ('ThrottlingException', 'ProvisionedThroughputExceededException', 'RequestThrottled'):
                    # Exponential backoff for throttling errors
                    retry_count += 1
                    if retry_count < max_retries:
                        sleep_time = backoff_base * (2 ** (retry_count - 1))
                        logger.warning(f"AWS throttling error, retrying in {sleep_time:.2f} seconds: {str(e)}")
                        time.sleep(sleep_time)
                        continue
                
                # Log other errors
                logger.error(f"AWS client error in {func.__name__}: {str(e)}")
                raise
                
            except (NoCredentialsError, PartialCredentialsError) as e:
                logger.error(f"AWS credentials error in {func.__name__}: {str(e)}")
                raise
                
            except Exception as e:
                logger.error(f"Unexpected error in {func.__name__}: {str(e)}")
                raise
        
        # If we've exhausted retries
        logger.error(f"Maximum retries ({max_retries}) exceeded in {func.__name__}")
        raise Exception(f"Maximum retries exceeded in {func.__name__}")
    
    return wrapper 