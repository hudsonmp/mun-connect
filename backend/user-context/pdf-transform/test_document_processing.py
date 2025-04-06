#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests for Document Processing Pipeline

This module contains tests for the document processing pipeline
with fixtures for both local and AWS-based testing.
"""

import os
import json
import tempfile
import unittest
import shutil
from unittest import mock
from pathlib import Path
from typing import Dict, Any, List

# Set test environment flag
os.environ["TEST_ENV"] = "true"

# Import pipeline components
from document_processing_pipeline import (
    DocumentProcessingPipeline, 
    MockDocumentProcessor,
    lambda_handler
)
from config import config_handler, TEST_CONFIG, S3_CONFIG, ENV_TEST_MODE

# Verify we're in test mode
assert ENV_TEST_MODE, "Tests must run with TEST_ENV=true"

# Test fixtures directory
FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "test_fixtures")


class TestDocumentFixtures:
    """Test fixtures for document processing tests"""
    
    @classmethod
    def setup_fixtures(cls):
        """Set up test fixtures if they don't exist"""
        # Create fixtures directory if it doesn't exist
        if not os.path.exists(FIXTURES_DIR):
            os.makedirs(FIXTURES_DIR)
            
            # Create subdirectories
            os.makedirs(os.path.join(FIXTURES_DIR, "input"), exist_ok=True)
            os.makedirs(os.path.join(FIXTURES_DIR, "output"), exist_ok=True)
            os.makedirs(os.path.join(FIXTURES_DIR, "s3"), exist_ok=True)
            
            # Create a sample PDF
            cls._create_sample_pdf()
            
            # Create a sample processed document
            cls._create_sample_processed_document()
    
    @staticmethod
    def _create_sample_pdf():
        """Create a simple PDF file for testing"""
        try:
            # Try to use reportlab to create a simple PDF
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter
            
            pdf_path = os.path.join(FIXTURES_DIR, "input", "sample_document.pdf")
            
            c = canvas.Canvas(pdf_path, pagesize=letter)
            c.setFont("Helvetica", 12)
            c.drawString(100, 750, "Sample Document for Testing")
            c.drawString(100, 730, "This is a test document created for unit testing.")
            c.drawString(100, 710, "It contains basic text that can be processed by the pipeline.")
            c.drawString(100, 690, "The document processing pipeline should be able to extract this text.")
            c.drawString(100, 650, "Country: Test Country")
            c.drawString(100, 630, "Committee: Test Committee")
            c.drawString(100, 610, "Topic: Test Topic")
            
            # Add some argument-like text
            c.drawString(100, 570, "Claim: The test system should work properly.")
            c.drawString(100, 550, "Premise: Good tests ensure system quality.")
            c.drawString(100, 530, "Premise: This test document is designed to test the system.")
            c.drawString(100, 510, "Conclusion: Therefore, this test should verify the system works.")
            
            c.save()
            
            print(f"Created sample PDF at {pdf_path}")
            
        except ImportError:
            # If reportlab is not available, create a text file with a .pdf extension
            # This won't be a valid PDF but can be used to test the pipeline's error handling
            pdf_path = os.path.join(FIXTURES_DIR, "input", "sample_document.pdf")
            
            with open(pdf_path, 'w') as f:
                f.write("This is not a real PDF, but a text file with a .pdf extension for testing error handling.")
            
            print(f"Created mock PDF (text file) at {pdf_path}")
    
    @staticmethod
    def _create_sample_processed_document():
        """Create a sample processed document JSON file"""
        output_path = os.path.join(FIXTURES_DIR, "output", "sample_document_processed.json")
        
        # Sample processed document
        sample_doc = {
            "metadata": {
                "document_type": "test_document",
                "page_count": 1,
                "title": "Sample Document for Testing",
                "committee": "Test Committee",
                "country": "Test Country",
                "main_topic": "Test Topic",
                "discussed_topics": ["Testing", "Document Processing", "Mock Data"]
            },
            "content": {
                "full_text": "Sample Document for Testing\nThis is a test document created for unit testing.\nIt contains basic text that can be processed by the pipeline.\nThe document processing pipeline should be able to extract this text.\nCountry: Test Country\nCommittee: Test Committee\nTopic: Test Topic\nClaim: The test system should work properly.\nPremise: Good tests ensure system quality.\nPremise: This test document is designed to test the system.\nConclusion: Therefore, this test should verify the system works.",
                "sentences": [
                    "Sample Document for Testing.",
                    "This is a test document created for unit testing.",
                    "It contains basic text that can be processed by the pipeline.",
                    "The document processing pipeline should be able to extract this text.",
                    "Country: Test Country.",
                    "Committee: Test Committee.",
                    "Topic: Test Topic.",
                    "Claim: The test system should work properly.",
                    "Premise: Good tests ensure system quality.",
                    "Premise: This test document is designed to test the system.",
                    "Conclusion: Therefore, this test should verify the system works."
                ],
                "paragraphs": [
                    "Sample Document for Testing. This is a test document created for unit testing.",
                    "It contains basic text that can be processed by the pipeline. The document processing pipeline should be able to extract this text.",
                    "Country: Test Country. Committee: Test Committee. Topic: Test Topic.",
                    "Claim: The test system should work properly. Premise: Good tests ensure system quality. Premise: This test document is designed to test the system. Conclusion: Therefore, this test should verify the system works."
                ]
            },
            "bert_friendly": {
                "segments": [
                    "Sample Document for Testing. This is a test document created for unit testing.",
                    "It contains basic text that can be processed by the pipeline. The document processing pipeline should be able to extract this text.",
                    "Country: Test Country. Committee: Test Committee. Topic: Test Topic.",
                    "Claim: The test system should work properly. Premise: Good tests ensure system quality. Premise: This test document is designed to test the system. Conclusion: Therefore, this test should verify the system works."
                ],
                "segment_count": 4
            },
            "linguistic_features": {
                "word_count": 100,
                "sentence_count": 11,
                "avg_sentence_length": 9.09,
                "avg_word_length": 4.5,
                "type_token_ratio": 0.65,
                "unique_word_count": 65,
                "flesch_reading_ease": 70.5,
                "flesch_kincaid_grade": 8.2,
                "passive_voice_ratio": 0.09,
                "question_ratio": 0.0,
                "exclamation_ratio": 0.0,
                "sentiment_polarity": 0.2,
                "positive_word_ratio": 0.15,
                "negative_word_ratio": 0.05
            },
            "argumentation": {
                "components": [
                    {
                        "text": "The test system should work properly.",
                        "type": "claim",
                        "score": 0.95,
                        "start_idx": 345,
                        "end_idx": 381
                    },
                    {
                        "text": "Good tests ensure system quality.",
                        "type": "premise",
                        "score": 0.92,
                        "start_idx": 391,
                        "end_idx": 425
                    },
                    {
                        "text": "This test document is designed to test the system.",
                        "type": "premise",
                        "score": 0.89,
                        "start_idx": 435,
                        "end_idx": 484
                    },
                    {
                        "text": "Therefore, this test should verify the system works.",
                        "type": "conclusion",
                        "score": 0.93,
                        "start_idx": 498,
                        "end_idx": 547
                    }
                ],
                "relations": [
                    {
                        "source": 1,  # First premise (index in components)
                        "target": 0,  # Claim (index in components)
                        "type": "support",
                        "score": 0.88
                    },
                    {
                        "source": 2,  # Second premise (index in components)
                        "target": 0,  # Claim (index in components)
                        "type": "support",
                        "score": 0.85
                    },
                    {
                        "source": 3,  # Conclusion (index in components)
                        "target": 0,  # Claim (index in components)
                        "type": "support",
                        "score": 0.90
                    }
                ],
                "metrics": {
                    "component_counts": {
                        "claim": 1,
                        "premise": 2,
                        "conclusion": 1
                    },
                    "component_percentages": {
                        "claim": 25.0,
                        "premise": 50.0,
                        "conclusion": 25.0
                    },
                    "argument_density": 0.36,
                    "premise_to_claim_ratio": 2.0,
                    "support_to_attack_ratio": 3.0,
                    "reasoning_counts": {
                        "causal": 1,
                        "example": 1,
                        "authority": 0,
                        "definition": 0,
                        "analogy": 0
                    },
                    "reasoning_diversity": 0.4
                }
            },
            "processing_metadata": {
                "processing_time": 1.25,
                "timestamp": 1617283200.0,
                "original_path": "test_fixtures/input/sample_document.pdf",
                "document_type": "test_document",
                "environment": "test"
            }
        }
        
        # Save the sample document
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(sample_doc, f, indent=2, ensure_ascii=False)
        
        print(f"Created sample processed document at {output_path}")
        
        return sample_doc


class TestDocumentProcessingPipelineLocal(unittest.TestCase):
    """Test the document processing pipeline in local mode"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures and environment"""
        # Create test fixtures
        TestDocumentFixtures.setup_fixtures()
        
        # Create a temp directory for test output
        cls.temp_dir = tempfile.mkdtemp()
        
        # Path to sample document
        cls.sample_pdf_path = os.path.join(FIXTURES_DIR, "input", "sample_document.pdf")
        
        # Mock the PDF processor
        cls.mock_processor = MockDocumentProcessor()
    
    @classmethod
    def tearDownClass(cls):
        """Clean up temporary files"""
        # Remove the temp directory
        shutil.rmtree(cls.temp_dir)
    
    def test_init_with_defaults(self):
        """Test initialization with default options"""
        pipeline = DocumentProcessingPipeline(
            output_dir=self.temp_dir,
            lazy_loading=True  # Use lazy loading for faster tests
        )
        
        # Check that the pipeline was initialized
        self.assertIsNotNone(pipeline)
        self.assertEqual(pipeline.output_dir, self.temp_dir)
        self.assertTrue(pipeline.lazy_loading)
    
    @mock.patch('document_processing_pipeline.pdf_processor', new_callable=lambda: MockDocumentProcessor())
    def test_process_document(self, mock_pdf_processor):
        """Test processing a document"""
        pipeline = DocumentProcessingPipeline(
            output_dir=self.temp_dir,
            lazy_loading=False  # Force eager loading
        )
        
        # Replace processors with mocks
        pipeline.pdf_processor = mock_pdf_processor
        
        # Process the document
        output_path, document_data = pipeline.process_document(self.sample_pdf_path, "test_document")
        
        # Check the results
        self.assertTrue(os.path.exists(output_path))
        self.assertIsInstance(document_data, dict)
        self.assertIn("content", document_data)
        self.assertIn("metadata", document_data)
        self.assertEqual(document_data["metadata"]["document_type"], "test_document")
    
    def test_extract_profile(self):
        """Test extracting a profile from a processed document"""
        # Load the sample processed document
        with open(os.path.join(FIXTURES_DIR, "output", "sample_document_processed.json"), 'r') as f:
            processed_doc = json.load(f)
        
        pipeline = DocumentProcessingPipeline(
            output_dir=self.temp_dir,
            lazy_loading=True  # Use lazy loading for faster tests
        )
        
        # Extract profile
        profile = pipeline.extract_profile(processed_doc)
        
        # Check the profile
        self.assertIsInstance(profile, dict)
        self.assertIn("metadata", profile)
        self.assertIn("writing_style", profile)
        self.assertIn("argumentation", profile)
        self.assertEqual(profile["metadata"]["document_type"], "test_document")
        self.assertEqual(profile["metadata"]["country"], "Test Country")
    
    def test_aggregate_profiles(self):
        """Test aggregating multiple profiles"""
        # Load the sample processed document
        with open(os.path.join(FIXTURES_DIR, "output", "sample_document_processed.json"), 'r') as f:
            processed_doc = json.load(f)
        
        pipeline = DocumentProcessingPipeline(
            output_dir=self.temp_dir,
            lazy_loading=True
        )
        
        # Extract profile
        profile = pipeline.extract_profile(processed_doc)
        
        # Aggregate profiles (using the same profile twice for simplicity)
        aggregate = pipeline.aggregate_profiles([profile, profile])
        
        # Check the aggregate profile
        self.assertIsInstance(aggregate, dict)
        self.assertIn("metadata", aggregate)
        self.assertEqual(aggregate["metadata"]["document_count"], 2)
        self.assertIn("test_document", aggregate["metadata"]["document_types"])
        self.assertEqual(aggregate["metadata"]["document_types"]["test_document"], 2)


@unittest.skipIf(not os.environ.get("RUN_AWS_TESTS"), "Skipping AWS tests, set RUN_AWS_TESTS=true to run")
class TestDocumentProcessingPipelineAWS(unittest.TestCase):
    """Test the document processing pipeline in AWS mode (requires AWS credentials)"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures and environment"""
        # Create test fixtures
        TestDocumentFixtures.setup_fixtures()
        
        # Create a temp directory for test output
        cls.temp_dir = tempfile.mkdtemp()
        
        # Path to sample document
        cls.sample_pdf_path = os.path.join(FIXTURES_DIR, "input", "sample_document.pdf")
        
        # Set up S3 test bucket if needed
        cls.test_bucket = TEST_CONFIG["test_s3_bucket"]
        
        # Upload test file to S3 if AWS tests are enabled
        if os.environ.get("RUN_AWS_TESTS") and os.environ.get("PDF_TRANSFORM_TEST_S3_BUCKET"):
            try:
                import boto3
                s3 = boto3.client('s3')
                
                # Create bucket if it doesn't exist
                try:
                    s3.head_bucket(Bucket=cls.test_bucket)
                except Exception:
                    # Create bucket in us-east-1
                    s3.create_bucket(Bucket=cls.test_bucket)
                
                # Upload sample PDF
                test_key = "test/sample_document.pdf"
                s3.upload_file(cls.sample_pdf_path, cls.test_bucket, test_key)
                cls.s3_pdf_path = f"s3://{cls.test_bucket}/{test_key}"
                
                print(f"Uploaded test file to {cls.s3_pdf_path}")
            except Exception as e:
                print(f"Failed to set up S3 test environment: {str(e)}")
                # Set to None to skip S3 tests
                cls.s3_pdf_path = None
        else:
            cls.s3_pdf_path = None
    
    @classmethod
    def tearDownClass(cls):
        """Clean up temporary files"""
        # Remove the temp directory
        shutil.rmtree(cls.temp_dir)
        
        # Clean up S3 test files if needed
        if os.environ.get("RUN_AWS_TESTS") and cls.s3_pdf_path and os.environ.get("CLEANUP_TEST_S3"):
            try:
                import boto3
                s3 = boto3.client('s3')
                
                # Parse the S3 path
                parts = cls.s3_pdf_path[5:].split('/', 1)
                bucket = parts[0]
                key = parts[1]
                
                # Delete the test file
                s3.delete_object(Bucket=bucket, Key=key)
                
                # Delete the output file if it exists
                output_key = f"{S3_CONFIG['output_prefix']}{os.path.basename(key).split('.')[0]}_processed.json"
                try:
                    s3.delete_object(Bucket=bucket, Key=output_key)
                except Exception:
                    pass
                
                print(f"Cleaned up S3 test files in {bucket}")
            except Exception as e:
                print(f"Failed to clean up S3 test environment: {str(e)}")
    
    @unittest.skipIf(not os.environ.get("PDF_TRANSFORM_TEST_S3_BUCKET"), "Skipping S3 test, no test bucket configured")
    def test_s3_integration(self):
        """Test S3 integration for document processing"""
        if not self.s3_pdf_path:
            self.skipTest("S3 test file not available")
        
        # Initialize pipeline with S3 bucket
        pipeline = DocumentProcessingPipeline(
            output_dir=self.temp_dir,
            s3_bucket=self.test_bucket,
            lazy_loading=True  # Use lazy loading for tests
        )
        
        # Mock the processors to avoid actual processing
        pipeline._initialize_processors = mock.MagicMock()
        pipeline.pdf_processor = MockDocumentProcessor()
        
        # Test S3 download
        local_path = pipeline._download_from_s3(self.s3_pdf_path)
        self.assertTrue(os.path.exists(local_path))
        
        # Test S3 upload
        s3_path = pipeline._upload_to_s3(local_path)
        self.assertTrue(s3_path.startswith("s3://"))
    
    def test_lambda_handler(self):
        """Test the Lambda handler function"""
        # Create a mock Lambda event
        event = {
            "s3_bucket": self.test_bucket,
            "s3_key": "test/sample_document.pdf",
            "document_type": "test_document",
            "processing_options": {
                "use_markdown": True,
                "use_spacy": False,
                "use_transformers": False,
                "parallel_processing": False,
                "lazy_loading": True
            }
        }
        
        # Mock the entire document processing to return a basic response
        with mock.patch('document_processing_pipeline.DocumentProcessingPipeline') as MockPipeline:
            # Configure the mock to return a sample result
            mock_instance = MockPipeline.return_value
            mock_instance.process_document.return_value = (
                f"s3://{self.test_bucket}/processed/sample_document_processed.json",
                {
                    "metadata": {"document_type": "test_document", "page_count": 1},
                    "processing_metadata": {"processing_time": 1.25}
                }
            )
            
            # Call the Lambda handler
            response = lambda_handler(event, {})
            
            # Check the response
            self.assertEqual(response["statusCode"], 200)
            self.assertIn("body", response)
            
            # Parse the body
            body = json.loads(response["body"])
            self.assertIn("message", body)
            self.assertIn("output_path", body)
            self.assertIn("metadata", body)
            
            # Verify the pipeline was called
            MockPipeline.assert_called_once()
            mock_instance.process_document.assert_called_once()


if __name__ == "__main__":
    unittest.main() 