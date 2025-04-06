"""
Test script for AWS integration with DelegateAnalyzer.

This script tests the integration of DelegateAnalyzer with AWS services
including Lambda, S3, and ECS.
"""

import os
import sys
import json
import unittest
import boto3
import tempfile
from unittest.mock import patch, MagicMock
from botocore.exceptions import ClientError

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the module being tested
from delegate_analyzer import DelegateAnalyzer, lambda_handler, container_handler, get_analyzer_instance
from test_fixtures import (
    TEST_DOCUMENTS, 
    MOCK_STYLE_ANALYSIS, 
    MOCK_POSITION_ANALYSIS,
    create_test_country_db,
    get_mock_lambda_event,
    get_mock_s3_event,
    MockAnalyzer
)

class TestAWSIntegration(unittest.TestCase):
    """Test AWS integration with DelegateAnalyzer"""
    
    def setUp(self):
        """Set up test environment"""
        # Set up environment variables for testing
        os.environ["TEST_ENV"] = "true"
        os.environ["STORAGE_MODE"] = "s3"
        os.environ["DELEGATE_ANALYZER_S3_BUCKET"] = "test-bucket"
        os.environ["DELEGATE_ANALYZER_S3_REGION"] = "us-east-1"
        os.environ["USE_CPU_ONLY"] = "true"
        
        # Create temporary file for country database
        self.country_db_path = create_test_country_db()
        os.environ["DELEGATE_ANALYZER_COUNTRY_DB_PATH"] = self.country_db_path
        
        # Reset singleton instance
        global _instance
        _instance = None
    
    def tearDown(self):
        """Clean up after tests"""
        # Clean up environment variables
        for key in [
            "TEST_ENV", 
            "STORAGE_MODE", 
            "DELEGATE_ANALYZER_S3_BUCKET", 
            "DELEGATE_ANALYZER_S3_REGION",
            "DELEGATE_ANALYZER_COUNTRY_DB_PATH",
            "USE_CPU_ONLY"
        ]:
            if key in os.environ:
                del os.environ[key]
        
        # Remove temporary file
        if os.path.exists(self.country_db_path):
            os.remove(self.country_db_path)
    
    @patch('boto3.client')
    def test_init_s3_handler(self, mock_boto_client):
        """Test S3 handler initialization"""
        # Mock S3 client
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3
        
        # Test initialization
        analyzer = DelegateAnalyzer(self.country_db_path)
        
        # Check if boto3.client was called with the right parameters
        mock_boto_client.assert_called_with('s3', region_name='us-east-1')
        
        # Check if head_bucket was called with the right parameters
        mock_s3.head_bucket.assert_called_with(Bucket='test-bucket')
    
    @patch('boto3.client')
    @patch('delegate_analyzer.StyleAnalyzer')
    @patch('delegate_analyzer.CountryPositionAnalyzer')
    def test_analyze_document(self, mock_country_analyzer, mock_style_analyzer, mock_boto_client):
        """Test document analysis with AWS integration"""
        # Mock S3 client
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3
        
        # Mock analyzers
        mock_style_instance = MagicMock()
        mock_style_instance.analyze_style.return_value = MOCK_STYLE_ANALYSIS
        mock_style_analyzer.return_value = mock_style_instance
        
        mock_country_instance = MagicMock()
        mock_country_instance.analyze_position_alignment.return_value = MOCK_POSITION_ANALYSIS
        mock_country_analyzer.return_value = mock_country_instance
        
        # Initialize analyzer
        analyzer = DelegateAnalyzer(self.country_db_path)
        
        # Test document analysis
        doc = TEST_DOCUMENTS[0]
        result = analyzer.analyze_document(doc["text"], doc["country"], doc["committee"])
        
        # Check if analyzers were called with the right parameters
        mock_style_instance.analyze_style.assert_called_with(doc["text"], doc["country"], doc["committee"])
        mock_country_instance.analyze_position_alignment.assert_called_with(doc["text"], doc["country"])
        
        # Check if result was saved to S3
        mock_s3.put_object.assert_called()
    
    @patch('boto3.client')
    @patch('delegate_analyzer.StyleAnalyzer')
    @patch('delegate_analyzer.CountryPositionAnalyzer')
    def test_s3_document_download(self, mock_country_analyzer, mock_style_analyzer, mock_boto_client):
        """Test downloading document from S3"""
        # Mock S3 client
        mock_s3 = MagicMock()
        mock_response = {'Body': MagicMock()}
        mock_response['Body'].read.return_value = TEST_DOCUMENTS[0]["text"].encode('utf-8')
        mock_s3.get_object.return_value = mock_response
        mock_boto_client.return_value = mock_s3
        
        # Mock analyzers
        mock_style_instance = MagicMock()
        mock_style_instance.analyze_style.return_value = MOCK_STYLE_ANALYSIS
        mock_style_analyzer.return_value = mock_style_instance
        
        mock_country_instance = MagicMock()
        mock_country_instance.analyze_position_alignment.return_value = MOCK_POSITION_ANALYSIS
        mock_country_analyzer.return_value = mock_country_instance
        
        # Initialize analyzer
        analyzer = DelegateAnalyzer(self.country_db_path)
        
        # Test document download and analysis
        s3_path = "s3://test-bucket/documents/test_doc.txt"
        result = analyzer._get_document_from_s3(s3_path)
        
        # Check if get_object was called with the right parameters
        mock_s3.get_object.assert_called_with(Bucket='test-bucket', Key='documents/test_doc.txt')
        
        # Check if the document text was returned
        self.assertEqual(result, TEST_DOCUMENTS[0]["text"])
    
    @patch('boto3.client')
    @patch('delegate_analyzer.StyleAnalyzer')
    @patch('delegate_analyzer.CountryPositionAnalyzer')
    def test_lambda_handler(self, mock_country_analyzer, mock_style_analyzer, mock_boto_client):
        """Test Lambda handler function"""
        # Mock S3 client
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3
        
        # Mock analyzers
        mock_style_instance = MagicMock()
        mock_style_instance.analyze_style.return_value = MOCK_STYLE_ANALYSIS
        mock_style_analyzer.return_value = mock_style_instance
        
        mock_country_instance = MagicMock()
        mock_country_instance.analyze_position_alignment.return_value = MOCK_POSITION_ANALYSIS
        mock_country_analyzer.return_value = mock_country_instance
        
        # Test Lambda handler with document analysis
        event = get_mock_lambda_event("analyze_document")
        context = {}
        response = lambda_handler(event, context)
        
        # Check if response is correct
        self.assertEqual(response['statusCode'], 200)
        self.assertIn('body', response)
        
        # Test Lambda handler with S3 path
        event = get_mock_s3_event("analyze_document")
        
        # Mock S3 document download
        mock_response = {'Body': MagicMock()}
        mock_response['Body'].read.return_value = TEST_DOCUMENTS[0]["text"].encode('utf-8')
        mock_s3.get_object.return_value = mock_response
        
        response = lambda_handler(event, context)
        
        # Check if response is correct
        self.assertEqual(response['statusCode'], 200)
        self.assertIn('body', response)
        
        # Test Lambda handler with multiple document analysis
        event = get_mock_lambda_event("analyze_multiple_documents")
        response = lambda_handler(event, context)
        
        # Check if response is correct
        self.assertEqual(response['statusCode'], 200)
        self.assertIn('body', response)
    
    @patch('boto3.client')
    @patch('delegate_analyzer.StyleAnalyzer')
    @patch('delegate_analyzer.CountryPositionAnalyzer')
    def test_container_handler(self, mock_country_analyzer, mock_style_analyzer, mock_boto_client):
        """Test container handler function"""
        # Mock S3 client
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3
        
        # Mock analyzers
        mock_style_instance = MagicMock()
        mock_style_instance.analyze_style.return_value = MOCK_STYLE_ANALYSIS
        mock_style_analyzer.return_value = mock_style_instance
        
        mock_country_instance = MagicMock()
        mock_country_instance.analyze_position_alignment.return_value = MOCK_POSITION_ANALYSIS
        mock_country_analyzer.return_value = mock_country_instance
        
        # Test container handler with document analysis
        request = get_mock_lambda_event("analyze_document")
        response = container_handler(request)
        
        # Check if response is correct
        self.assertEqual(response['status'], 'success')
        self.assertIn('result', response)
        
        # Test container handler with multiple document analysis
        request = get_mock_lambda_event("analyze_multiple_documents")
        response = container_handler(request)
        
        # Check if response is correct
        self.assertEqual(response['status'], 'success')
        self.assertIn('result', response)
    
    @patch('delegate_analyzer.DelegateAnalyzer')
    def test_singleton_pattern(self, mock_delegate_analyzer):
        """Test singleton pattern for analyzer instance"""
        # Get first instance
        instance1 = get_analyzer_instance(self.country_db_path)
        
        # Check if DelegateAnalyzer was called
        mock_delegate_analyzer.assert_called_once_with(self.country_db_path)
        
        # Reset mock
        mock_delegate_analyzer.reset_mock()
        
        # Get second instance
        instance2 = get_analyzer_instance(self.country_db_path)
        
        # Check if DelegateAnalyzer was not called again
        mock_delegate_analyzer.assert_not_called()
        
        # Check if instances are the same
        self.assertEqual(instance1, instance2)

if __name__ == '__main__':
    unittest.main() 