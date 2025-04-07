import os
import sys
import pytest
import boto3
import json
from pathlib import Path
from dotenv import load_dotenv

# Add project root directory to path
project_root = Path(__file__).parents[1]
sys.path.insert(0, str(project_root))

# Load environment variables from .env file
load_dotenv()

# Create test data directories if they don't exist
TEST_DATA_DIR = Path(__file__).parent / "test_data"
TEST_OUTPUT_DIR = Path(__file__).parent / "test_output"
os.makedirs(TEST_DATA_DIR, exist_ok=True)
os.makedirs(TEST_OUTPUT_DIR, exist_ok=True)

@pytest.fixture(scope="session")
def aws_credentials():
    """Mocked AWS Credentials for boto3."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"

@pytest.fixture(scope="session")
def s3_client(aws_credentials):
    """Create a mock S3 client."""
    from moto import mock_s3
    with mock_s3():
        conn = boto3.client("s3", region_name="us-east-1")
        # Create a test bucket
        conn.create_bucket(Bucket="test-bucket")
        yield conn

@pytest.fixture(scope="session")
def sample_pdf_file():
    """Create a sample PDF file for testing."""
    from backend.user_context.pdf_transform.pdf_processor import create_test_pdf
    pdf_path = TEST_DATA_DIR / "test_document.pdf"
    create_test_pdf(str(pdf_path))
    return str(pdf_path)

@pytest.fixture(scope="session")
def supabase_mock():
    """Mock Supabase client."""
    class SupabaseMock:
        def __init__(self):
            self.tables = {}
            self.current_query = None
            self.auth = AuthMock()
        
        def table(self, name):
            if name not in self.tables:
                self.tables[name] = []
            self.current_query = {"table": name, "filters": []}
            return self
            
        def insert(self, data):
            self.current_query["action"] = "insert"
            self.current_query["data"] = data
            return self
            
        def update(self, data):
            self.current_query["action"] = "update"
            self.current_query["data"] = data
            return self
            
        def delete(self):
            self.current_query["action"] = "delete"
            return self
            
        def eq(self, field, value):
            self.current_query["filters"].append({"field": field, "op": "eq", "value": value})
            return self
            
        def execute(self):
            table = self.current_query["table"]
            action = self.current_query.get("action")
            
            if action == "insert":
                data = self.current_query["data"]
                if isinstance(data, list):
                    for item in data:
                        item["id"] = len(self.tables[table]) + 1
                        self.tables[table].append(item)
                else:
                    data["id"] = len(self.tables[table]) + 1
                    self.tables[table].append(data)
                return type('obj', (object,), {'data': [data]})
                
            # More operations can be added as needed
            
            # Return empty result if action not handled
            return type('obj', (object,), {'data': []})
            
        def raw(self, query):
            return query
    
    class AuthMock:
        def sign_up(self, email, password):
            return {"user": {"id": "test-user-id", "email": email}, "session": {"access_token": "test-token"}}
            
        def sign_in_with_email(self, email, password):
            return {"user": {"id": "test-user-id", "email": email}, "session": {"access_token": "test-token"}}
    
    return SupabaseMock()

@pytest.fixture(scope="function")
def sagemaker_mock():
    """Mock SageMaker client."""
    class SageMakerMock:
        def __init__(self):
            self.endpoints = {}
            
        def invoke_endpoint(self, EndpointName, Body, ContentType="application/json"):
            # Just echo back the input with a mock prediction
            try:
                input_data = json.loads(Body)
                response = {
                    "prediction": "mock_prediction",
                    "input_received": input_data
                }
                return {
                    "Body": json.dumps(response).encode(),
                    "ContentType": "application/json"
                }
            except:
                return {
                    "Body": json.dumps({"error": "Invalid input"}).encode(),
                    "ContentType": "application/json"
                }
    
    return SageMakerMock()

@pytest.fixture(scope="session")
def test_app():
    """Create a test Flask app."""
    from flask import Flask
    from flask.testing import FlaskClient
    
    app = Flask("test_app")
    app.config['TESTING'] = True
    
    # Import and register your blueprints here
    try:
        from backend.mind_map.api import mind_map_blueprint
        app.register_blueprint(mind_map_blueprint, url_prefix="/mind-map")
    except ImportError:
        pass
    
    # More blueprints can be registered as needed
    
    return app

@pytest.fixture(scope="function")
def test_client(test_app):
    """Create a test client."""
    with test_app.test_client() as client:
        yield client 