import json
import pytest
import boto3
import os
from unittest import mock

@pytest.mark.aws
def test_s3_integration(s3_client, aws_credentials):
    """Test basic S3 integration."""
    # Upload a test file
    test_content = json.dumps({"test": "data"}).encode('utf-8')
    s3_client.put_object(
        Bucket="test-bucket",
        Key="test-file.json",
        Body=test_content,
        ContentType="application/json"
    )
    
    # Check if the file exists
    response = s3_client.list_objects_v2(Bucket="test-bucket")
    assert "Contents" in response
    assert any(obj["Key"] == "test-file.json" for obj in response["Contents"])
    
    # Download the file
    download_response = s3_client.get_object(Bucket="test-bucket", Key="test-file.json")
    downloaded_content = download_response["Body"].read()
    assert downloaded_content == test_content

@pytest.mark.aws
def test_sagemaker_integration(sagemaker_mock):
    """Test SageMaker integration."""
    from backend.user_context.pdf_transform.aws_helpers import LambdaHelper
    
    # Create a mock for boto3.client
    def mock_boto3_client(*args, **kwargs):
        if args[0] == 'sagemaker-runtime':
            return sagemaker_mock
        # Return a different mock for other services if needed
        return mock.MagicMock()
    
    # Apply the mock
    with mock.patch('boto3.client', side_effect=mock_boto3_client):
        # Create a SageMaker client
        from backend.user_context.comparison_fingerprint.mun_analysis_tool import SageMakerHandler
        
        # Create a new instance with our mock
        handler = SageMakerHandler(endpoint_name="test-endpoint")
        
        # Test invoking the endpoint
        response = handler.invoke_endpoint({"text": "Test input"})
        
        # Verify the response
        assert "prediction" in response
        assert response["input_received"]["text"] == "Test input"

@pytest.mark.aws
def test_document_processing_with_aws(sagemaker_mock, s3_client, monkeypatch):
    """Test document processing with AWS integration."""
    # Mock the necessary AWS services
    monkeypatch.setattr('boto3.client', lambda service, region_name=None: {
        's3': s3_client,
        'sagemaker-runtime': sagemaker_mock,
        'lambda': mock.MagicMock(),
        'cloudwatch': mock.MagicMock(),
    }.get(service, mock.MagicMock()))
    
    # Create test data
    test_data = {
        "text": "This is a test document for processing.",
        "metadata": {
            "document_type": "position_paper",
            "committee": "Test Committee",
            "country": "Test Country"
        }
    }
    
    # Test uploading to S3
    from backend.user_context.pdf_transform.document_processing_pipeline import DocumentProcessingPipeline
    
    # Create a pipeline instance
    pipeline = DocumentProcessingPipeline(
        use_transformers=False,  # Simplify for testing
        parallel_processing=False,
        use_gpu=False,
        s3_bucket="test-bucket"
    )
    
    # Mock the extract_profile method to return test data
    monkeypatch.setattr(
        pipeline, 
        'extract_profile', 
        lambda processed_document: {
            "style": {
                "formality": "high",
                "complexity": "medium"
            },
            "content": {
                "topics": ["test", "mock"]
            }
        }
    )
    
    # Process a "document" (our test data)
    with mock.patch('builtins.open', mock.mock_open(read_data=json.dumps(test_data))):
        # Create a test file
        test_file = "test_document.json"
        with open(test_file, 'w') as f:
            json.dump(test_data, f)
        
        # Process the document
        result_path, profile = pipeline.process_document(test_file)
        
        # Verify the result
        assert profile is not None
        assert "style" in profile
        assert profile["style"]["formality"] == "high"

@pytest.mark.aws
def test_lambda_handler_integration():
    """Test Lambda handler integration."""
    # Create a Lambda event
    event = {
        "body": json.dumps({
            "action": "process",
            "document_type": "position_paper"
        }),
        "httpMethod": "POST",
        "path": "/process"
    }
    
    # Test the Lambda handler
    from backend.user_context.pdf_transform.api import lambda_handler
    
    # Mock the necessary functions
    with mock.patch('backend.user_context.pdf_transform.api.process_document_handler') as mock_handler:
        mock_handler.return_value = {
            "statusCode": 200,
            "body": json.dumps({"result": "success"})
        }
        
        # Call the handler
        response = lambda_handler(event, None)
        
        # Verify the response
        assert response["statusCode"] == 200
        assert "body" in response
        body = json.loads(response["body"])
        assert body["result"] == "success" 