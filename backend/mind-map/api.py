from flask import Blueprint, request, jsonify
import os
import json
import logging
from typing import Dict, Any, Optional, Union
import numpy as np
import uuid

from .mind_map_generator import MindMapGenerator
from .indexer import MindMapIndexer

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create the blueprint
mind_map_blueprint = Blueprint('mind_map', __name__)

# Initialize the generator and indexer
mind_map_generator = MindMapGenerator()
mind_map_indexer = MindMapIndexer(index_dir="backend/mind-map/indices")

# Create a cache for mind maps
_mind_map_cache = {}

@mind_map_blueprint.route('/generate-base', methods=['POST'])
def generate_base_mind_map():
    """
    Generate a base mind map from a committee background guide.
    
    Request body:
    {
        "background_guide_content": "Full text of the background guide",
        "session_id": "Optional session ID"
    }
    
    Returns:
        JSON response with the base mind map
    """
    try:
        data = request.json
        
        # Extract required fields
        background_guide_content = data.get('background_guide_content')
        session_id = data.get('session_id', str(uuid.uuid4()))
        
        # Validate input
        if not background_guide_content:
            return jsonify({"error": "Background guide content is required"}), 400
        
        # Generate the base mind map
        base_mind_map = mind_map_generator.generate_base_mind_map(background_guide_content)
        
        # Store in cache
        _mind_map_cache[session_id] = {"base_mind_map": base_mind_map}
        
        return jsonify({
            "session_id": session_id,
            "base_mind_map": base_mind_map
        }), 200
    
    except Exception as e:
        logger.error(f"Error generating base mind map: {e}")
        return jsonify({"error": str(e)}), 500

@mind_map_blueprint.route('/customize', methods=['POST'])
def customize_mind_map():
    """
    Customize a base mind map with country-specific and delegate-specific information.
    
    Request body:
    {
        "session_id": "Session ID from generate-base",
        "country": "Country name",
        "delegate_profile": {...},  # Delegate profile information
        "base_mind_map": {...}      # Optional: provide the base mind map if not cached
    }
    
    Returns:
        JSON response with the customized mind map
    """
    try:
        data = request.json
        
        # Extract required fields
        session_id = data.get('session_id')
        country = data.get('country')
        delegate_profile = data.get('delegate_profile', {})
        
        # Either get the base mind map from cache or from the request
        base_mind_map = None
        if session_id in _mind_map_cache and "base_mind_map" in _mind_map_cache[session_id]:
            base_mind_map = _mind_map_cache[session_id]["base_mind_map"]
        elif "base_mind_map" in data:
            base_mind_map = data["base_mind_map"]
        
        # Validate input
        if not session_id:
            return jsonify({"error": "Session ID is required"}), 400
        if not country:
            return jsonify({"error": "Country is required"}), 400
        if not base_mind_map:
            return jsonify({"error": "Base mind map not found"}), 404
        
        # Get OpenAI API key from environment
        openai_api_key = os.environ.get("OPENAI_API_KEY")
        if not openai_api_key:
            return jsonify({"error": "OpenAI API key not configured"}), 500
        
        # Customize the mind map
        customized_result = mind_map_generator.customize_mind_map(
            base_mind_map, country, delegate_profile, openai_api_key)
        
        # Store in cache
        if session_id in _mind_map_cache:
            _mind_map_cache[session_id]["customized_mind_map"] = customized_result
        else:
            _mind_map_cache[session_id] = {"customized_mind_map": customized_result}
        
        return jsonify({
            "session_id": session_id,
            "research_json": customized_result["research_json"],
            "visualization_json": customized_result["visualization_json"]
        }), 200
    
    except Exception as e:
        logger.error(f"Error customizing mind map: {e}")
        return jsonify({"error": str(e)}), 500

@mind_map_blueprint.route('/index', methods=['POST'])
def index_mind_map():
    """
    Index a mind map for efficient retrieval during paper generation.
    
    Request body:
    {
        "session_id": "Session ID from customize",
        "research_json": {...}  # Optional: provide the research JSON if not cached
    }
    
    Returns:
        JSON response with index information
    """
    try:
        data = request.json
        
        # Extract required fields
        session_id = data.get('session_id')
        
        # Either get the research JSON from cache or from the request
        research_json = None
        if session_id in _mind_map_cache and "customized_mind_map" in _mind_map_cache[session_id]:
            research_json = _mind_map_cache[session_id]["customized_mind_map"]["research_json"]
        elif "research_json" in data:
            research_json = data["research_json"]
        
        # Validate input
        if not session_id:
            return jsonify({"error": "Session ID is required"}), 400
        if not research_json:
            return jsonify({"error": "Research JSON not found"}), 404
        
        # Index the mind map
        indexed_mind_map = mind_map_generator.index_mind_map(research_json)
        
        # Create a FAISS index
        index_path = mind_map_indexer.create_index(indexed_mind_map, session_id)
        
        # Store in cache
        if session_id in _mind_map_cache:
            _mind_map_cache[session_id]["indexed_mind_map"] = indexed_mind_map
        else:
            _mind_map_cache[session_id] = {"indexed_mind_map": indexed_mind_map}
        
        return jsonify({
            "session_id": session_id,
            "index_path": index_path,
            "status": "indexed"
        }), 200
    
    except Exception as e:
        logger.error(f"Error indexing mind map: {e}")
        return jsonify({"error": str(e)}), 500

@mind_map_blueprint.route('/search', methods=['POST'])
def search_mind_map():
    """
    Search a mind map for relevant content based on a query.
    
    Request body:
    {
        "session_id": "Session ID from index",
        "query": "The search query",
        "k": 5  # Optional: number of results to return
    }
    
    Returns:
        JSON response with search results
    """
    try:
        data = request.json
        
        # Extract required fields
        session_id = data.get('session_id')
        query = data.get('query')
        k = int(data.get('k', 5))
        
        # Validate input
        if not session_id:
            return jsonify({"error": "Session ID is required"}), 400
        if not query:
            return jsonify({"error": "Query is required"}), 400
        
        # Get the indexed mind map
        indexed_mind_map = None
        if session_id in _mind_map_cache and "indexed_mind_map" in _mind_map_cache[session_id]:
            indexed_mind_map = _mind_map_cache[session_id]["indexed_mind_map"]
        
        if not indexed_mind_map:
            return jsonify({"error": "Indexed mind map not found"}), 404
        
        # Generate embedding for the query
        query_embedding = mind_map_generator._generate_embedding(query)
        
        # Search the index
        results = mind_map_indexer.search(query_embedding, session_id, k)
        
        return jsonify({
            "session_id": session_id,
            "query": query,
            "results": results
        }), 200
    
    except Exception as e:
        logger.error(f"Error searching mind map: {e}")
        return jsonify({"error": str(e)}), 500

@mind_map_blueprint.route('/generate-for-paper', methods=['POST'])
def generate_for_paper():
    """
    Generate a mind map specifically for position paper generation.
    This is a combined endpoint that performs generation, customization, and indexing.
    
    Request body:
    {
        "background_guide_content": "Full text of the background guide",
        "country": "Country name",
        "delegate_profile": {...},  # Delegate profile information
        "session_id": "Optional session ID"
    }
    
    Returns:
        JSON response with the complete mind map for paper generation
    """
    try:
        data = request.json
        
        # Extract required fields
        background_guide_content = data.get('background_guide_content')
        country = data.get('country')
        delegate_profile = data.get('delegate_profile', {})
        session_id = data.get('session_id', str(uuid.uuid4()))
        
        # Validate input
        if not background_guide_content:
            return jsonify({"error": "Background guide content is required"}), 400
        if not country:
            return jsonify({"error": "Country is required"}), 400
        
        # Get OpenAI API key from environment
        openai_api_key = os.environ.get("OPENAI_API_KEY")
        if not openai_api_key:
            return jsonify({"error": "OpenAI API key not configured"}), 500
        
        # Step 1: Generate base mind map
        base_mind_map = mind_map_generator.generate_base_mind_map(background_guide_content)
        
        # Step 2: Customize the mind map
        customized_result = mind_map_generator.customize_mind_map(
            base_mind_map, country, delegate_profile, openai_api_key)
        
        # Step 3: Index the mind map
        indexed_mind_map = mind_map_generator.index_mind_map(customized_result["research_json"])
        
        # Step 4: Create a FAISS index
        index_path = mind_map_indexer.create_index(indexed_mind_map, session_id)
        
        # Store everything in cache
        _mind_map_cache[session_id] = {
            "base_mind_map": base_mind_map,
            "customized_mind_map": customized_result,
            "indexed_mind_map": indexed_mind_map
        }
        
        return jsonify({
            "session_id": session_id,
            "research_json": customized_result["research_json"],
            "visualization_json": customized_result["visualization_json"],
            "index_path": index_path,
            "status": "complete"
        }), 200
    
    except Exception as e:
        logger.error(f"Error in complete mind map generation: {e}")
        return jsonify({"error": str(e)}), 500

@mind_map_blueprint.route('/<session_id>', methods=['GET'])
def get_mind_map(session_id):
    """
    Get a mind map by session ID.
    
    Returns:
        JSON response with the requested mind map
    """
    try:
        # Validate input
        if not session_id:
            return jsonify({"error": "Session ID is required"}), 400
        
        # Check if the session exists in cache
        if session_id not in _mind_map_cache:
            return jsonify({"error": "Mind map not found"}), 404
        
        # Return the requested mind map data
        session_data = _mind_map_cache[session_id]
        
        # Prepare response based on what's available
        response = {"session_id": session_id}
        
        if "base_mind_map" in session_data:
            response["base_mind_map"] = session_data["base_mind_map"]
            
        if "customized_mind_map" in session_data:
            customized = session_data["customized_mind_map"]
            response["research_json"] = customized["research_json"]
            response["visualization_json"] = customized["visualization_json"]
            
        if "indexed_mind_map" in session_data:
            response["status"] = "indexed"
        elif "customized_mind_map" in session_data:
            response["status"] = "customized"
        elif "base_mind_map" in session_data:
            response["status"] = "base"
        
        return jsonify(response), 200
    
    except Exception as e:
        logger.error(f"Error retrieving mind map: {e}")
        return jsonify({"error": str(e)}), 500

@mind_map_blueprint.route('/<session_id>', methods=['DELETE'])
def delete_mind_map(session_id):
    """
    Delete a mind map and its associated index.
    
    Returns:
        JSON response with deletion status
    """
    try:
        # Validate input
        if not session_id:
            return jsonify({"error": "Session ID is required"}), 400
        
        # Check if the session exists in cache
        if session_id not in _mind_map_cache:
            return jsonify({"error": "Mind map not found"}), 404
        
        # Delete from cache
        del _mind_map_cache[session_id]
        
        # Delete the index if it exists
        mind_map_indexer.delete_index(session_id)
        
        return jsonify({
            "session_id": session_id,
            "status": "deleted"
        }), 200
    
    except Exception as e:
        logger.error(f"Error deleting mind map: {e}")
        return jsonify({"error": str(e)}), 500 