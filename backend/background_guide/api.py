"""
Background Guide API

Flask API endpoints for the background guide processor.
"""

import os
import json
import tempfile
from typing import Dict, List, Any
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename

from .processor import BackgroundGuideProcessor

# Initialize the blueprint
bg_blueprint = Blueprint('background_guide', __name__)

# Global processor instance
processor = None

def get_processor():
    """Get or initialize the background guide processor."""
    global processor
    if processor is None:
        output_dir = os.path.join(tempfile.gettempdir(), "bg_processor_output")
        os.makedirs(output_dir, exist_ok=True)
        processor = BackgroundGuideProcessor(
            use_openai_for_summary=True,
            use_aws_model=True,
            output_dir=output_dir
        )
    return processor

# Routes
@bg_blueprint.route('/process', methods=['POST'])
def process_background_guide():
    """
    Process a background guide file and extract information.
    
    Expected input:
    - Form data with file input 'file'
    - Optional form field 'use_openai' (default: 'true')
    - Optional form field 'use_aws' (default: 'true')
    
    Returns JSON with processing results.
    """
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400
    
    # Get config options
    use_openai = request.form.get('use_openai', 'true').lower() == 'true'
    use_aws = request.form.get('use_aws', 'true').lower() == 'true'
    
    # Save file to temp location
    filename = secure_filename(file.filename)
    temp_dir = tempfile.mkdtemp()
    file_path = os.path.join(temp_dir, filename)
    file.save(file_path)
    
    try:
        # Get or initialize processor
        processor = get_processor()
        processor.use_openai_for_summary = use_openai
        processor.use_aws_model = use_aws
        
        # Process the file
        results = processor.process_file(file_path)
        
        # Prepare response
        response = {
            "success": True,
            "file_name": filename,
            "output_dir": processor.output_dir,
            "segment_count": len(results.get("segments", [])),
            "json_files": {k: os.path.basename(v) for k, v in results.get("json_files", {}).items()},
            "summaries": results.get("summaries", [])[:3]  # Include a few summaries as preview
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        current_app.logger.error(f"Error processing file: {str(e)}")
        return jsonify({"error": f"Error processing file: {str(e)}"}), 500
    finally:
        # Cleanup temp file
        if os.path.exists(file_path):
            os.remove(file_path)
        if os.path.exists(temp_dir):
            os.rmdir(temp_dir)

@bg_blueprint.route('/generate-custom-guide', methods=['POST'])
def generate_custom_guide():
    """
    Generate a custom background guide for a specific topic using RAG.
    
    Expected input:
    - JSON with 'query' field
    - Optional 'model' field (default: 'gpt-4o-mini')
    
    Returns JSON with generated guide content.
    """
    data = request.json
    if not data or 'query' not in data:
        return jsonify({"error": "Query is required"}), 400
    
    query = data.get('query')
    model = data.get('model', 'gpt-4o-mini')
    
    try:
        # Get processor
        processor = get_processor()
        
        # Generate custom guide
        guide_content = processor.generate_custom_guide(query, openai_model=model)
        
        return jsonify({
            "success": True,
            "query": query,
            "model": model,
            "content": guide_content
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error generating custom guide: {str(e)}")
        return jsonify({"error": f"Error generating custom guide: {str(e)}"}), 500

@bg_blueprint.route('/retrieve-context', methods=['POST'])
def retrieve_context_for_query():
    """
    Retrieve relevant context for a query from the indexed document.
    
    Expected input:
    - JSON with 'query' field
    - Optional 'top_k' field (default: 3)
    
    Returns JSON with retrieved context.
    """
    data = request.json
    if not data or 'query' not in data:
        return jsonify({"error": "Query is required"}), 400
    
    query = data.get('query')
    top_k = int(data.get('top_k', 3))
    
    try:
        # Get processor
        processor = get_processor()
        
        # Check if we have an index
        index_dir = os.path.join(processor.output_dir, "index")
        if not os.path.exists(index_dir):
            return jsonify({
                "error": "No index found. Process a document first."
            }), 400
        
        # Retrieve context
        context = processor.retrieve_context_for_query(query, top_k)
        
        return jsonify({
            "success": True,
            "query": query,
            "context": context
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error retrieving context: {str(e)}")
        return jsonify({"error": f"Error retrieving context: {str(e)}"}), 500

@bg_blueprint.route('/extract-text', methods=['POST'])
def extract_text():
    """
    Extract text from a file without full processing.
    
    Expected input:
    - Form data with file input 'file'
    
    Returns JSON with extracted text.
    """
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400
    
    # Save file to temp location
    filename = secure_filename(file.filename)
    temp_dir = tempfile.mkdtemp()
    file_path = os.path.join(temp_dir, filename)
    file.save(file_path)
    
    try:
        from .extraction import extract_text_from_pdf, clean_text
        
        if file_path.lower().endswith('.pdf'):
            text = extract_text_from_pdf(file_path)
        else:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
        
        # Clean the text
        cleaned_text = clean_text(text)
        
        # Truncate text for preview if very long
        preview = cleaned_text[:5000] + "..." if len(cleaned_text) > 5000 else cleaned_text
        
        return jsonify({
            "success": True,
            "file_name": filename,
            "text_length": len(cleaned_text),
            "preview": preview
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error extracting text: {str(e)}")
        return jsonify({"error": f"Error extracting text: {str(e)}"}), 500
    finally:
        # Cleanup temp file
        if os.path.exists(file_path):
            os.remove(file_path)
        if os.path.exists(temp_dir):
            os.rmdir(temp_dir) 