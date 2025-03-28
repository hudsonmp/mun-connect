from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import db

app = Flask(__name__)
CORS(app)

# Authentication routes
@app.route('/api/auth/signup', methods=['POST'])
def signup():
    data = request.json
    try:
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({"error": "Email and password are required"}), 400
            
        # Call Supabase signup
        response = db.sign_up(email, password)
        
        # Return user data in the expected format
        return jsonify({
            "user": response.user.dict() if response.user else None,
            "session": response.session.dict() if response.session else None
        }), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/auth/signin', methods=['POST'])
def signin():
    data = request.json
    try:
        email = data.get('email')
        password = data.get('password')
        response = db.sign_in(email, password)
        return jsonify(response.dict()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/auth/signout', methods=['POST'])
def signout():
    try:
        db.sign_out()
        return jsonify({"message": "Successfully signed out"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/auth/reset-password', methods=['POST'])
def reset_password():
    data = request.json
    try:
        email = data.get('email')
        db.reset_password(email)
        return jsonify({"message": "Password reset email sent"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# Add session route
@app.route('/api/auth/session', methods=['GET'])
def session():
    try:
        # Get session from request headers
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({"error": "No authorization header"}), 401
            
        # Verify session with Supabase
        session = db.supabase.auth.get_session()
        return jsonify({
            "session": session.dict() if session else None
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 401

# Conference routes
@app.route('/api/conferences', methods=['GET'])
def get_conferences():
    try:
        user_id = request.headers.get('user-id')
        if not user_id:
            return jsonify({"error": "User ID required"}), 400
        
        response = db.get_conferences(user_id)
        return jsonify(response.data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/conferences/<int:conference_id>', methods=['GET'])
def get_conference(conference_id):
    try:
        user_id = request.headers.get('user-id')
        if not user_id:
            return jsonify({"error": "User ID required"}), 400
        
        response = db.get_conference(conference_id, user_id)
        return jsonify(response.data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/conferences', methods=['POST'])
def create_conference():
    try:
        user_id = request.headers.get('user-id')
        if not user_id:
            return jsonify({"error": "User ID required"}), 400
        
        data = request.json
        response = db.create_conference(user_id, data)
        
        # Update user stats
        stats = db.get_user_stats(user_id).data
        db.update_user_stats(user_id, {
            "conferences_count": stats.get("conferences_count", 0) + 1
        })
        
        return jsonify(response.data), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/conferences/<int:conference_id>', methods=['PUT'])
def update_conference(conference_id):
    try:
        user_id = request.headers.get('user-id')
        if not user_id:
            return jsonify({"error": "User ID required"}), 400
        
        data = request.json
        response = db.update_conference(conference_id, user_id, data)
        return jsonify(response.data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/conferences/<int:conference_id>', methods=['DELETE'])
def delete_conference(conference_id):
    try:
        user_id = request.headers.get('user-id')
        if not user_id:
            return jsonify({"error": "User ID required"}), 400
        
        response = db.delete_conference(conference_id, user_id)
        
        # Update user stats
        stats = db.get_user_stats(user_id).data
        if stats.get("conferences_count", 0) > 0:
            db.update_user_stats(user_id, {
                "conferences_count": stats.get("conferences_count") - 1
            })
        
        return jsonify(response.data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# Document routes
@app.route('/api/documents', methods=['GET'])
def get_documents():
    try:
        user_id = request.headers.get('user-id')
        if not user_id:
            return jsonify({"error": "User ID required"}), 400
        
        response = db.get_documents(user_id)
        return jsonify(response.data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/documents/<int:document_id>', methods=['GET'])
def get_document(document_id):
    try:
        user_id = request.headers.get('user-id')
        if not user_id:
            return jsonify({"error": "User ID required"}), 400
        
        response = db.get_document(document_id, user_id)
        return jsonify(response.data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/documents', methods=['POST'])
def create_document():
    try:
        user_id = request.headers.get('user-id')
        if not user_id:
            return jsonify({"error": "User ID required"}), 400
        
        data = request.json
        response = db.create_document(user_id, data)
        
        # Update user stats
        stats = db.get_user_stats(user_id).data
        db.update_user_stats(user_id, {
            "documents_count": stats.get("documents_count", 0) + 1
        })
        
        return jsonify(response.data), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/documents/<int:document_id>', methods=['PUT'])
def update_document(document_id):
    try:
        user_id = request.headers.get('user-id')
        if not user_id:
            return jsonify({"error": "User ID required"}), 400
        
        data = request.json
        response = db.update_document(document_id, user_id, data)
        return jsonify(response.data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/documents/<int:document_id>', methods=['DELETE'])
def delete_document(document_id):
    try:
        user_id = request.headers.get('user-id')
        if not user_id:
            return jsonify({"error": "User ID required"}), 400
        
        response = db.delete_document(document_id, user_id)
        
        # Update user stats
        stats = db.get_user_stats(user_id).data
        if stats.get("documents_count", 0) > 0:
            db.update_user_stats(user_id, {
                "documents_count": stats.get("documents_count") - 1
            })
        
        return jsonify(response.data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# User stats routes
@app.route('/api/user-stats', methods=['GET'])
def get_stats():
    try:
        user_id = request.headers.get('user-id')
        if not user_id:
            return jsonify({"error": "User ID required"}), 400
        
        response = db.get_user_stats(user_id)
        return jsonify(response.data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/user-stats/awards', methods=['PUT'])
def update_awards():
    try:
        user_id = request.headers.get('user-id')
        if not user_id:
            return jsonify({"error": "User ID required"}), 400
        
        data = request.json
        awards_count = data.get('awards_count')
        
        response = db.update_user_stats(user_id, {
            "awards_count": awards_count
        })
        
        return jsonify(response.data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# AI features placeholder
@app.route('/api/ai/generate-document', methods=['POST'])
def generate_document():
    # This is a placeholder for AI document generation
    return jsonify({"message": "AI document generation placeholder"}), 200

@app.route('/api/ai/improve-document', methods=['POST'])
def improve_document():
    # This is a placeholder for AI document improvement
    return jsonify({"message": "AI document improvement placeholder"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True) 