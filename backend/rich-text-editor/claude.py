from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import json
from datetime import datetime
import os
import uuid
import openai  # For AI integration

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configure database
DATABASE = 'mun_editor.db'

# Configure OpenAI for AI integration
# openai.api_key = os.environ.get("OPENAI_API_KEY")
# In a production app, you would use environment variables for the API key

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with app.app_context():
        conn = get_db_connection()
        conn.execute('''
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                user_id TEXT
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS versions (
                id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                version_number INTEGER NOT NULL,
                content TEXT NOT NULL,
                title TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (document_id) REFERENCES documents (id)
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS citations (
                id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                citation_type TEXT NOT NULL,
                author TEXT,
                year TEXT,
                title TEXT,
                publisher TEXT,
                journal TEXT,
                volume TEXT,
                issue TEXT,
                pages TEXT,
                url TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (document_id) REFERENCES documents (id)
            )
        ''')
        conn.commit()
        conn.close()

# Initialize the database
init_db()

# Routes
@app.route('/api/documents', methods=['GET'])
def get_documents():
    user_id = request.args.get('user_id', default=None)
    
    conn = get_db_connection()
    if user_id:
        documents = conn.execute('SELECT * FROM documents WHERE user_id = ? ORDER BY updated_at DESC',
                               (user_id,)).fetchall()
    else:
        documents = conn.execute('SELECT * FROM documents ORDER BY updated_at DESC').fetchall()
    
    conn.close()
    
    return jsonify([dict(doc) for doc in documents])

@app.route('/api/documents', methods=['POST'])
def create_document():
    data = request.json
    document_id = str(uuid.uuid4())
    
    conn = get_db_connection()
    conn.execute('INSERT INTO documents (id, title, user_id) VALUES (?, ?, ?)',
               (document_id, data.get('title', 'Untitled Document'), data.get('user_id')))
    
    # Create initial version
    version_id = str(uuid.uuid4())
    conn.execute('INSERT INTO versions (id, document_id, version_number, content, title) VALUES (?, ?, ?, ?, ?)',
               (version_id, document_id, 1, data.get('content', ''), 'Initial Version'))
    
    conn.commit()
    conn.close()
    
    return jsonify({'document_id': document_id, 'version_id': version_id})

@app.route('/api/documents/<document_id>', methods=['GET'])
def get_document(document_id):
    conn = get_db_connection()
    document = conn.execute('SELECT * FROM documents WHERE id = ?', (document_id,)).fetchone()
    
    if not document:
        conn.close()
        return jsonify({'error': 'Document not found'}), 404
    
    # Get the latest version by default
    version = conn.execute('''
        SELECT * FROM versions 
        WHERE document_id = ? 
        ORDER BY version_number DESC 
        LIMIT 1
    ''', (document_id,)).fetchone()
    
    # Get all citations for this document
    citations = conn.execute('SELECT * FROM citations WHERE document_id = ?', (document_id,)).fetchall()
    
    conn.close()
    
    return jsonify({
        'document': dict(document),
        'version': dict(version) if version else None,
        'citations': [dict(citation) for citation in citations]
    })

@app.route('/api/documents/<document_id>/versions', methods=['GET'])
def get_document_versions(document_id):
    conn = get_db_connection()
    versions = conn.execute('''
        SELECT * FROM versions 
        WHERE document_id = ? 
        ORDER BY version_number DESC
    ''', (document_id,)).fetchall()
    
    conn.close()
    
    return jsonify([dict(version) for version in versions])

@app.route('/api/documents/<document_id>/versions', methods=['POST'])
def create_version(document_id):
    data = request.json
    
    conn = get_db_connection()
    # Check if document exists
    document = conn.execute('SELECT * FROM documents WHERE id = ?', (document_id,)).fetchone()
    
    if not document:
        conn.close()
        return jsonify({'error': 'Document not found'}), 404
    
    # Get the latest version number
    latest_version = conn.execute('''
        SELECT MAX(version_number) as max_version 
        FROM versions 
        WHERE document_id = ?
    ''', (document_id,)).fetchone()
    
    new_version_number = 1
    if latest_version and latest_version['max_version']:
        new_version_number = latest_version['max_version'] + 1
    
    # Create new version
    version_id = str(uuid.uuid4())
    conn.execute('''
        INSERT INTO versions (id, document_id, version_number, content, title) 
        VALUES (?, ?, ?, ?, ?)
    ''', (
        version_id, 
        document_id, 
        new_version_number, 
        data.get('content', ''), 
        data.get('title', f'Version {new_version_number}')
    ))
    
    # Update document updated_at timestamp
    conn.execute('''
        UPDATE documents 
        SET updated_at = CURRENT_TIMESTAMP, title = ? 
        WHERE id = ?
    ''', (data.get('document_title', document['title']), document_id))
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'version_id': version_id,
        'version_number': new_version_number
    })

@app.route('/api/documents/<document_id>/versions/<version_number>', methods=['GET'])
def get_specific_version(document_id, version_number):
    conn = get_db_connection()
    version = conn.execute('''
        SELECT * FROM versions 
        WHERE document_id = ? AND version_number = ?
    ''', (document_id, version_number)).fetchone()
    
    conn.close()
    
    if not version:
        return jsonify({'error': 'Version not found'}), 404
    
    return jsonify(dict(version))

@app.route('/api/documents/<document_id>/citations', methods=['POST'])
def add_citation(document_id):
    data = request.json
    citation_id = str(uuid.uuid4())
    
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO citations (
            id, document_id, citation_type, author, year, title, 
            publisher, journal, volume, issue, pages, url
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        citation_id,
        document_id,
        data.get('type', 'book'),
        data.get('author', ''),
        data.get('year', ''),
        data.get('title', ''),
        data.get('publisher', ''),
        data.get('journal', ''),
        data.get('volume', ''),
        data.get('issue', ''),
        data.get('pages', ''),
        data.get('url', '')
    ))
    
    conn.commit()
    conn.close()
    
    return jsonify({'citation_id': citation_id})

@app.route('/api/ai-suggestions', methods=['POST'])
def get_ai_suggestions():
    data = request.json
    content = data.get('content', '')
    
    try:
        # In a real application, you would use OpenAI API here
        # response = openai.Completion.create(
        #     engine="text-davinci-003",
        #     prompt=f"The following is a part of a Model UN document. Please provide suggestions to improve it:\n\n{content}\n\nSuggestions:",
        #     max_tokens=150,
        #     n=1,
        #     stop=None,
        #     temperature=0.7,
        # )
        # suggestion = response.choices[0].text.strip()
        
        # For demo purposes, we'll return a mock response
        if "climate" in content.lower():
            suggestion = "Consider strengthening your position statement on climate action by referencing the latest IPCC report. Also, your economic impact analysis could benefit from more specific data points."
        elif "security" in content.lower():
            suggestion = "Your security council resolution could be improved by adding more specific peacekeeping provisions and clearer enforcement mechanisms."
        elif "health" in content.lower():
            suggestion = "Consider adding more references to WHO guidelines in your public health proposals. Your funding mechanism could be more detailed."
        else:
            suggestion = "Your document would benefit from more specific country positions and clearer action points. Consider adding more statistical evidence to support your claims."
        
        return jsonify({
            'suggestion': suggestion
        })
    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500

if __name__ == '__main__':
    app.run(debug=True)