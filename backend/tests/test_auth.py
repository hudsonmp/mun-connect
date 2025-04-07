import pytest
import json
import os
import jwt
from unittest import mock
from datetime import datetime, timedelta

@pytest.fixture
def mock_jwt_token():
    """Generate a mock JWT token for testing."""
    # Create a token that expires in 1 hour
    expiration = datetime.utcnow() + timedelta(hours=1)
    
    # Create the payload
    payload = {
        "sub": "test-user-id",
        "email": "test@example.com",
        "exp": int(expiration.timestamp()),
        "iat": int(datetime.utcnow().timestamp()),
        "iss": "test-issuer"
    }
    
    # Sign the token with a test secret
    token = jwt.encode(payload, "test-secret", algorithm="HS256")
    return token

@pytest.fixture
def expired_jwt_token():
    """Generate an expired JWT token for testing."""
    # Create a token that expired 1 hour ago
    expiration = datetime.utcnow() - timedelta(hours=1)
    
    # Create the payload
    payload = {
        "sub": "test-user-id",
        "email": "test@example.com",
        "exp": int(expiration.timestamp()),
        "iat": int(datetime.utcnow().timestamp()),
        "iss": "test-issuer"
    }
    
    # Sign the token with a test secret
    token = jwt.encode(payload, "test-secret", algorithm="HS256")
    return token

@pytest.mark.auth
def test_supabase_auth_sign_up(supabase_mock):
    """Test user sign-up with Supabase."""
    # Test sign-up
    response = supabase_mock.auth.sign_up(
        email="test@example.com",
        password="password123"
    )
    
    # Verify the response
    assert response["user"]["email"] == "test@example.com"
    assert "access_token" in response["session"]

@pytest.mark.auth
def test_supabase_auth_sign_in(supabase_mock):
    """Test user sign-in with Supabase."""
    # Test sign-in
    response = supabase_mock.auth.sign_in_with_email(
        email="test@example.com",
        password="password123"
    )
    
    # Verify the response
    assert response["user"]["email"] == "test@example.com"
    assert "access_token" in response["session"]

@pytest.mark.auth
def test_jwt_validation(mock_jwt_token, expired_jwt_token):
    """Test JWT token validation."""
    # Function to validate JWT tokens
    def validate_token(token, secret="test-secret"):
        try:
            payload = jwt.decode(token, secret, algorithms=["HS256"])
            return payload, None
        except jwt.ExpiredSignatureError:
            return None, "Token expired"
        except jwt.InvalidTokenError:
            return None, "Invalid token"
    
    # Test valid token
    payload, error = validate_token(mock_jwt_token)
    assert error is None
    assert payload["sub"] == "test-user-id"
    assert payload["email"] == "test@example.com"
    
    # Test expired token
    payload, error = validate_token(expired_jwt_token)
    assert payload is None
    assert error == "Token expired"
    
    # Test invalid token
    payload, error = validate_token("invalid-token")
    assert payload is None
    assert error == "Invalid token"

@pytest.mark.auth
def test_protected_endpoint(test_client, mock_jwt_token, monkeypatch):
    """Test a protected endpoint with authentication."""
    # Mock the auth middleware
    def mock_verify_token(token):
        if token == mock_jwt_token:
            return {"sub": "test-user-id", "email": "test@example.com"}
        return None
    
    # Create a test Flask route with auth
    @test_app.route('/protected', methods=['GET'])
    def protected_route():
        # Extract token from header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({"error": "Unauthorized"}), 401
        
        token = auth_header.split(' ')[1]
        user = mock_verify_token(token)
        
        if not user:
            return jsonify({"error": "Invalid token"}), 401
        
        return jsonify({"message": "Success", "user": user}), 200
    
    # Register the route with the app
    monkeypatch.setattr(
        'flask.request', 
        type('obj', (object,), {
            'headers': {
                'Authorization': f'Bearer {mock_jwt_token}'
            }
        })
    )
    
    # Test with valid token
    response = test_client.get(
        '/protected',
        headers={'Authorization': f'Bearer {mock_jwt_token}'}
    )
    
    # Verify response
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["message"] == "Success"
    assert data["user"]["sub"] == "test-user-id"
    
    # Test with invalid token
    response = test_client.get(
        '/protected',
        headers={'Authorization': 'Bearer invalid-token'}
    )
    
    # Verify response
    assert response.status_code == 401 