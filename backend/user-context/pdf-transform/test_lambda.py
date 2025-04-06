#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test Script for Document Processing Lambda API

This script provides utilities for testing the Lambda API locally and creating
test events that simulate API Gateway requests.
"""

import os
import json
import base64
import argparse
import requests
from pathlib import Path
from io import BytesIO

# Import TestClient if api.py is available
try:
    from api import TestClient
    test_client_available = True
except ImportError:
    test_client_available = False

def setup_test_environment():
    """Set up test environment variables"""
    os.environ['TEST_ENV'] = 'true'
    os.environ['USE_S3'] = 'false'  # Default to local filesystem for tests
    
    # Create necessary directories
    os.makedirs('temp_uploads', exist_ok=True)
    os.makedirs('temp_output', exist_ok=True)

def generate_test_pdf(output_path="test_document.pdf"):
    """
    Generate a test PDF file.
    
    Args:
        output_path: Path to save the test PDF
        
    Returns:
        Path to the generated PDF file
    """
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        
        c = canvas.Canvas(output_path, pagesize=letter)
        
        # Add title
        c.setFont("Helvetica-Bold", 16)
        c.drawString(100, 750, "Test Document for Lambda Processing")
        
        # Add content
        c.setFont("Helvetica", 12)
        c.drawString(100, 700, "Country: Test Country")
        c.drawString(100, 680, "Committee: Test Committee")
        c.drawString(100, 660, "Topic: Climate Change")
        
        # Add paragraphs
        y_position = 620
        for i in range(1, 6):
            c.setFont("Helvetica", 14)
            c.drawString(100, y_position, f"Section {i}")
            y_position -= 20
            
            c.setFont("Helvetica", 12)
            c.drawString(120, y_position, f"This is the content of section {i}. It contains sample text")
            y_position -= 20
            c.drawString(120, y_position, f"that should be processed by the document processing pipeline.")
            y_position -= 40
        
        c.save()
        return output_path
    
    except ImportError:
        print("ReportLab not installed. Cannot generate test PDF.")
        return None

def create_test_event(event_type, pdf_path=None):
    """
    Create a test event that simulates an API Gateway request.
    
    Args:
        event_type: Type of event to create ('process', 'batch', 'download', 'health')
        pdf_path: Path to a test PDF file (for 'process' and 'batch' events)
        
    Returns:
        Lambda event dictionary
    """
    if event_type == 'process' and pdf_path:
        # Read PDF file
        with open(pdf_path, 'rb') as f:
            pdf_data = f.read()
        
        # Base64 encode PDF
        encoded_pdf = base64.b64encode(pdf_data).decode('utf-8')
        
        # Create event
        return {
            'httpMethod': 'POST',
            'path': '/process',
            'queryStringParameters': {
                'document_type': 'position_paper',
                'filename': os.path.basename(pdf_path)
            },
            'body': json.dumps({
                'file': encoded_pdf,
                'filename': os.path.basename(pdf_path),
                'document_type': 'position_paper'
            })
        }
    
    elif event_type == 'batch' and pdf_path:
        # For batch processing, duplicate the same PDF multiple times
        with open(pdf_path, 'rb') as f:
            pdf_data = f.read()
        
        # Base64 encode PDF
        encoded_pdf = base64.b64encode(pdf_data).decode('utf-8')
        
        # Create batch with 2 copies of the same file
        files = [
            {
                'file': encoded_pdf,
                'filename': f"copy1_{os.path.basename(pdf_path)}",
                'document_type': 'position_paper'
            },
            {
                'file': encoded_pdf,
                'filename': f"copy2_{os.path.basename(pdf_path)}",
                'document_type': 'speech'
            }
        ]
        
        # Create event
        return {
            'httpMethod': 'POST',
            'path': '/process-batch',
            'body': json.dumps({
                'files': files
            })
        }
    
    elif event_type == 'download':
        # Create download event
        return {
            'httpMethod': 'GET',
            'path': '/download/test_output.json',
            'pathParameters': {
                'filename': 'test_output.json'
            }
        }
    
    elif event_type == 'health':
        # Create health check event
        return {
            'httpMethod': 'GET',
            'path': '/health'
        }
    
    else:
        raise ValueError(f"Invalid event type: {event_type}")

def run_test(event_type, use_flask=False):
    """
    Run a test with the specified event type.
    
    Args:
        event_type: Type of event to test ('process', 'batch', 'download', 'health')
        use_flask: Whether to use Flask for testing
        
    Returns:
        Test result
    """
    setup_test_environment()
    
    # Generate test PDF if needed
    if event_type in ['process', 'batch']:
        pdf_path = generate_test_pdf()
        if not pdf_path:
            print("Could not generate test PDF")
            return None
    else:
        pdf_path = None
    
    # Create test event
    event = create_test_event(event_type, pdf_path)
    
    if use_flask and test_client_available:
        # Test using Flask
        from api import app
        with app.test_client() as client:
            if event_type == 'process':
                with open(pdf_path, 'rb') as f:
                    response = client.post(
                        '/process',
                        data={
                            'file': (BytesIO(f.read()), os.path.basename(pdf_path)),
                            'document_type': 'position_paper'
                        },
                        content_type='multipart/form-data'
                    )
                return response.get_json()
            
            elif event_type == 'batch':
                with open(pdf_path, 'rb') as f:
                    pdf_data = f.read()
                
                response = client.post(
                    '/process-batch',
                    data={
                        'files[]': [
                            (BytesIO(pdf_data), f"copy1_{os.path.basename(pdf_path)}"),
                            (BytesIO(pdf_data), f"copy2_{os.path.basename(pdf_path)}")
                        ]
                    },
                    content_type='multipart/form-data'
                )
                return response.get_json()
            
            elif event_type == 'download':
                response = client.get('/download/test_output.json')
                return response.data
            
            elif event_type == 'health':
                response = client.get('/health')
                return response.get_json()
    
    else:
        # Test using lambda_handler directly
        try:
            from api import lambda_handler
            
            # Call lambda_handler
            response = lambda_handler(event, None)
            
            # Parse response
            if 'body' in response and isinstance(response['body'], str):
                try:
                    body = json.loads(response['body'])
                    print(f"Status code: {response['statusCode']}")
                    return body
                except:
                    return response['body']
            
            return response
            
        except ImportError:
            # Try to use pdf_processor Lambda handler directly
            try:
                from pdf_processor import lambda_handler, create_test_pdf
                
                # Create appropriate event for pdf_processor Lambda handler
                if event_type == 'process':
                    with open(pdf_path, 'rb') as f:
                        pdf_data = f.read()
                    
                    pdf_event = {
                        'pdf_bytes': base64.b64encode(pdf_data).decode('utf-8'),
                        'filename': os.path.basename(pdf_path),
                        'document_type': 'position_paper',
                        'test_mode': True
                    }
                    
                    # Call lambda_handler
                    response = lambda_handler(pdf_event, None)
                    
                    if 'statusCode' in response and 'body' in response:
                        if isinstance(response['body'], str):
                            try:
                                return json.loads(response['body'])
                            except:
                                return response['body']
                        return response['body']
                    return response
                
                elif event_type == 'test_pdf':
                    # Test with auto-generated PDF
                    pdf_event = {
                        'test_pdf': True,
                        'document_type': 'position_paper',
                        'test_mode': True
                    }
                    
                    # Call lambda_handler
                    response = lambda_handler(pdf_event, None)
                    
                    if 'statusCode' in response and 'body' in response:
                        if isinstance(response['body'], str):
                            try:
                                return json.loads(response['body'])
                            except:
                                return response['body']
                        return response['body']
                    return response
                
                else:
                    print(f"Unsupported event type for direct pdf_processor testing: {event_type}")
                    return None
                
            except ImportError as e:
                print(f"Could not import lambda_handler: {e}")
                return None

def main():
    """Main function for command line usage"""
    parser = argparse.ArgumentParser(description='Test the document processing Lambda function')
    parser.add_argument('--type', default='process', choices=['process', 'batch', 'download', 'health', 'test_pdf'],
                        help='Type of test to run')
    parser.add_argument('--flask', action='store_true', help='Use Flask for testing')
    parser.add_argument('--pdf', help='Path to a custom PDF file for testing')
    parser.add_argument('--output', help='Path to save the output')
    args = parser.parse_args()
    
    # Override PDF path if provided
    if args.pdf and os.path.exists(args.pdf):
        if 'generate_test_pdf' in globals():
            original_fn = globals()['generate_test_pdf']
            globals()['generate_test_pdf'] = lambda output_path=None: args.pdf
    
    # Run test
    result = run_test(args.type, args.flask)
    
    # Save output if requested
    if args.output and result:
        with open(args.output, 'w') as f:
            if isinstance(result, dict) or isinstance(result, list):
                json.dump(result, f, indent=2)
            else:
                f.write(str(result))
        print(f"Saved output to {args.output}")
    
    # Print result
    if result:
        if isinstance(result, dict) or isinstance(result, list):
            print(json.dumps(result, indent=2))
        else:
            print(result)

def test_lambda_direct():
    """Test the Lambda function directly"""
    try:
        from pdf_processor import lambda_handler, create_test_pdf
        import tempfile
        
        # Create a test PDF
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
            temp_path = temp_file.name
        
        pdf_path = create_test_pdf(temp_path)
        print(f"Created test PDF at {pdf_path}")
        
        # Read PDF file and encode it
        with open(pdf_path, 'rb') as f:
            pdf_data = f.read()
        
        # Create test events
        test_events = [
            {
                'name': 'Test PDF bytes processing',
                'event': {
                    'pdf_bytes': base64.b64encode(pdf_data).decode('utf-8'),
                    'filename': 'test_document.pdf',
                    'document_type': 'position_paper',
                    'test_mode': True
                }
            },
            {
                'name': 'Test auto-generated PDF',
                'event': {
                    'test_pdf': True,
                    'document_type': 'position_paper',
                    'test_mode': True
                }
            }
        ]
        
        # Test each event
        for test in test_events:
            print(f"\n--- {test['name']} ---")
            response = lambda_handler(test['event'], None)
            
            if 'statusCode' in response:
                print(f"Status code: {response['statusCode']}")
                
                # Parse body if it's a string
                if 'body' in response and isinstance(response['body'], str):
                    try:
                        body = json.loads(response['body'])
                        # Print summary
                        if isinstance(body, dict):
                            for key, value in body.items():
                                if isinstance(value, dict):
                                    print(f"{key}: {len(value)} items")
                                elif isinstance(value, list):
                                    print(f"{key}: {len(value)} items")
                                else:
                                    print(f"{key}: {value}")
                        else:
                            print(body)
                    except:
                        print(response['body'])
                else:
                    print(response)
        
        # Clean up
        try:
            os.unlink(temp_path)
        except:
            pass
        
    except ImportError as e:
        print(f"Could not import required modules: {e}")

if __name__ == "__main__":
    main() 