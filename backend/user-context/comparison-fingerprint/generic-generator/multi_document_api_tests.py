#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test module for the Multi-Document Generator API.

This module provides unit tests for the Flask API and Lambda function.
"""

import os
import json
import unittest
import tempfile
import shutil
from unittest.mock import patch, MagicMock
import io

# Set up test environment variables
os.environ["TEST_ENV"] = "true"
os.environ["USE_S3"] = "false"
os.environ["XRAY_ENABLED"] = "false"

# Import after setting environment variables
import multi_document_api
from multi_document_api import app, create_test_client

class MockResponse:
    """Mock response for S3 operations"""
    def __init__(self, content):
        self.body = MagicMock()
        self.body.read.return_value = content

class TestMultiDocumentGeneratorAPI(unittest.TestCase):
    """Test class for the Multi-Document Generator API"""
    
    def setUp(self):
        """Set up test resources"""
        # Create temporary directories
        self.temp_dir = tempfile.mkdtemp()
        self.uploads_dir = os.path.join(self.temp_dir, "uploads")
        self.generated_dir = os.path.join(self.temp_dir, "generated_documents")
        os.makedirs(self.uploads_dir, exist_ok=True)
        os.makedirs(self.generated_dir, exist_ok=True)
        
        # Configure app for testing
        app.config['UPLOAD_FOLDER'] = self.uploads_dir
        app.config['TESTING'] = True
        
        # Create test client
        self.client = create_test_client()
        
        # Create test profile
        self.test_profile = {
            "delegateProfile": {
                "metadata": {
                    "committees": ["Security Council"],
                    "topics": ["Nuclear Disarmament"],
                    "time_period": ["2023"],
                    "roles": ["United States"]
                },
                "country": "United States",
                "committee": "Security Council"
            },
            "linguisticPatterns": {
                "vocabulary": {
                    "diversity": {"type_token_ratio": 0.65},
                    "formality": {"score": 0.8}
                }
            },
            "cognitiveFrameworks": {
                "reasoningPatterns": {
                    "dominant_reasoning": "deductive"
                }
            },
            "argumentativeStrategies": {
                "persuasiveTechniques": {
                    "dominant_appeal": "logos"
                }
            }
        }
        
        # Create a sample test profile file
        self.test_profile_path = os.path.join(self.uploads_dir, "test_profile.json")
        with open(self.test_profile_path, 'w') as f:
            json.dump(self.test_profile, f)
        
        # Create a sample generated document
        self.test_document = {
            "metadata": {
                "document_type": "position_paper",
                "committee": "Security Council",
                "country": "United States",
                "main_topic": "Nuclear Disarmament"
            },
            "content": {
                "full_text": "This is a test document.",
                "sentences": ["This is a test document."],
                "paragraphs": ["This is a test document."]
            },
            "generation_info": {
                "timestamp": "2023-01-01T00:00:00",
                "model": "test-model"
            }
        }
        
        self.test_document_path = os.path.join(self.generated_dir, "test_document.json")
        with open(self.test_document_path, 'w') as f:
            json.dump(self.test_document, f)
    
    def tearDown(self):
        """Clean up test resources"""
        # Remove temporary directory
        shutil.rmtree(self.temp_dir)
    
    @patch('multi_document_api.get_generator_instance')
    def test_health_check(self, mock_generator):
        """Test health check endpoint"""
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'healthy')
        self.assertIn('supported_document_types', data)
    
    @patch('multi_document_api.get_generator_instance')
    def test_document_types(self, mock_generator):
        """Test document types endpoint"""
        response = self.client.get('/document-types')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        
        # Check if all document types are returned
        self.assertIn('position_paper', data)
        self.assertIn('speech', data)
        self.assertIn('resolution', data)
        
        # Check if parameters are included
        self.assertIn('parameters', data['speech'])
        self.assertIn('parameters', data['resolution'])
    
    @patch('multi_document_api.MultiDocumentGenerator')
    @patch('multi_document_api.get_generator_instance')
    def test_generate_from_data(self, mock_get_generator, mock_generator_class):
        """Test generate from data endpoint"""
        # Setup mock generator
        mock_generator = MagicMock()
        mock_get_generator.return_value = mock_generator
        
        # Configure mock generator to return a test document
        mock_generator.generate_document.return_value = (
            self.test_document_path,
            {
                "metadata": self.test_document["metadata"],
                "generation_info": self.test_document["generation_info"]
            }
        )
        
        # Test request data
        request_data = {
            "document_type": "position_paper",
            "topic": "Nuclear Disarmament",
            "committee": "Security Council",
            "country": "United States",
            "profile": self.test_profile
        }
        
        # Send request
        response = self.client.post(
            '/generate-from-data',
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        # Check response
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertEqual(data['document_type'], 'position_paper')
        self.assertIn('output_file', data)
        
        # Verify mock was called with correct parameters
        mock_generator.generate_document.assert_called_once()
        args, kwargs = mock_generator.generate_document.call_args
        self.assertEqual(kwargs['document_type'], 'position_paper')
        self.assertEqual(kwargs['topic'], 'Nuclear Disarmament')
        self.assertEqual(kwargs['committee'], 'Security Council')
        self.assertEqual(kwargs['country'], 'United States')
    
    @patch('multi_document_api.s3_client')
    @patch('multi_document_api.MultiDocumentGenerator')
    @patch('multi_document_api.get_generator_instance')
    def test_download_file(self, mock_get_generator, mock_generator_class, mock_s3):
        """Test download file endpoint"""
        # Test with local file
        response = self.client.get(f'/download/test_document.json')
        self.assertEqual(response.status_code, 200)
        
        # Enable S3 to test that path
        multi_document_api.ENV_USE_S3 = True
        multi_document_api.IS_AWS = True
        multi_document_api.ENV_S3_BUCKET = "test-bucket"
        
        # Mock S3 client
        multi_document_api.s3_client = mock_s3
        
        # Mock head_object to indicate file exists
        mock_s3.head_object.return_value = {}
        
        # Mock generate_presigned_url
        mock_s3.generate_presigned_url.return_value = "https://test-bucket.s3.amazonaws.com/generated_documents/test_document.json"
        
        # Test with S3 file
        response = self.client.get(f'/download/test_document.json')
        self.assertEqual(response.status_code, 302)  # Redirect
        
        # Reset for other tests
        multi_document_api.ENV_USE_S3 = False
        multi_document_api.IS_AWS = False
        multi_document_api.s3_client = None
    
    @patch('multi_document_api.MultiDocumentGenerator')
    @patch('multi_document_api.get_generator_instance')
    def test_compare_documents(self, mock_get_generator, mock_generator_class):
        """Test compare documents endpoint"""
        # Create a second test document
        test_document2 = self.test_document.copy()
        test_document2["content"]["full_text"] = "This is a second test document."
        test_document2["content"]["sentences"] = ["This is a second test document."]
        test_document2["content"]["paragraphs"] = ["This is a second test document."]
        
        test_document2_path = os.path.join(self.generated_dir, "test_document2.json")
        with open(test_document2_path, 'w') as f:
            json.dump(test_document2, f)
        
        # Test request data
        request_data = {
            "original_path": self.test_document_path,
            "generated_path": test_document2_path
        }
        
        # Send request
        response = self.client.post(
            '/compare',
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        # Check response
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('comparison', data)
        self.assertIn('metadata', data['comparison'])
        self.assertIn('statistics', data['comparison'])
    
    @patch('multi_document_api.MultiDocumentGenerator')
    @patch('multi_document_api.get_generator_instance')
    def test_lambda_handler(self, mock_get_generator, mock_generator_class):
        """Test Lambda handler"""
        # Create mock Lambda event
        event = {
            "path": "/health",
            "httpMethod": "GET",
            "headers": {},
            "body": "{}"
        }
        
        # Save the original request global
        original_request = multi_document_api.request
        
        # Call Lambda handler
        response = multi_document_api.lambda_handler(event, {})
        
        # Restore original request
        multi_document_api.request = original_request
        
        # Check response
        self.assertEqual(response['statusCode'], 200)
        self.assertIn('body', response)
        self.assertIn('headers', response)
        
        # Parse body
        body = json.loads(response['body'])
        self.assertEqual(body['status'], 'test_success')


if __name__ == '__main__':
    unittest.main() 