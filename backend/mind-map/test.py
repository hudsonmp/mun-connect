#!/usr/bin/env python3
import os
import sys
import json
import argparse
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import mind map modules
from mind_map.mind_map_generator import MindMapGenerator
from mind_map.indexer import MindMapIndexer

def load_sample_background_guide(file_path):
    """Load a sample background guide from a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        logger.info(f"Loaded background guide from {file_path}")
        return content
    except Exception as e:
        logger.error(f"Error loading background guide: {e}")
        return None

def load_sample_delegate_profile():
    """Create a sample delegate profile for testing."""
    return {
        "user_id": "test_user",
        "country": "France",
        "committee": "UN General Assembly",
        "writing_style": {
            "formality": "high",
            "vocabulary_diversity": "moderate",
            "sentence_complexity": "high"
        },
        "linguistic_patterns": {
            "preferred_rhetorical_devices": ["parallelism", "metaphor"],
            "dominant_reasoning": "logical"
        },
        "interests": [
            "climate change", 
            "human rights", 
            "economic development"
        ],
        "experience_level": "intermediate"
    }

def test_mind_map_generation(background_guide_content, save_output=True):
    """Test the full mind map generation pipeline."""
    try:
        # Load environment variables
        load_dotenv()
        openai_api_key = os.environ.get("OPENAI_API_KEY")
        if not openai_api_key:
            logger.error("OPENAI_API_KEY not found in environment")
            return False
            
        # Initialize the generator and indexer
        generator = MindMapGenerator()
        indexer = MindMapIndexer(index_dir="indices")
        
        # Step 1: Generate base mind map
        logger.info("Generating base mind map...")
        base_mind_map = generator.generate_base_mind_map(background_guide_content)
        
        if save_output:
            with open("output_base_mind_map.json", "w") as f:
                json.dump(base_mind_map, f, indent=2)
            logger.info("Saved base mind map to output_base_mind_map.json")
        
        # Step 2: Customize the mind map
        logger.info("Customizing mind map...")
        delegate_profile = load_sample_delegate_profile()
        customized_results = generator.customize_mind_map(
            base_mind_map, 
            delegate_profile["country"], 
            delegate_profile, 
            openai_api_key
        )
        
        if save_output:
            with open("output_research_json.json", "w") as f:
                json.dump(customized_results["research_json"], f, indent=2)
            with open("output_visualization_json.json", "w") as f:
                json.dump(customized_results["visualization_json"], f, indent=2)
            logger.info("Saved customized mind maps to output files")
        
        # Step 3: Index the mind map
        logger.info("Indexing mind map...")
        indexed_mind_map = generator.index_mind_map(customized_results["research_json"])
        
        # Step 4: Create FAISS index
        session_id = "test_session"
        logger.info("Creating FAISS index...")
        index_path = indexer.create_index(indexed_mind_map, session_id)
        logger.info(f"Created index at {index_path}")
        
        # Step 5: Test search functionality
        logger.info("Testing search functionality...")
        test_query = "climate change impact on developing nations"
        query_embedding = generator._generate_embedding(test_query)
        
        search_results = indexer.search(query_embedding, session_id)
        
        if save_output:
            with open("output_search_results.json", "w") as f:
                json.dump({
                    "query": test_query,
                    "results": search_results
                }, f, indent=2)
            logger.info("Saved search results to output_search_results.json")
            
        logger.info("Search results:")
        for i, result in enumerate(search_results):
            logger.info(f"{i+1}. {result['node_id']} (score: {result['score']:.4f})")
            logger.info(f"   Content: {result['content'][:100]}...")
        
        # Clean up
        logger.info("Cleaning up...")
        indexer.delete_index(session_id)
        
        logger.info("Test completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Error in test: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    parser = argparse.ArgumentParser(description='Test Mind Map Generation')
    parser.add_argument('--input', type=str, help='Path to background guide file', default='sample_background_guide.txt')
    parser.add_argument('--no-save', action='store_true', help='Do not save output files')
    
    args = parser.parse_args()
    
    # Load the background guide
    content = load_sample_background_guide(args.input)
    if not content:
        logger.error("Failed to load background guide")
        sys.exit(1)
    
    # Run the test
    success = test_mind_map_generation(content, not args.no_save)
    
    if not success:
        logger.error("Test failed")
        sys.exit(1)
    
    sys.exit(0)

if __name__ == "__main__":
    main() 