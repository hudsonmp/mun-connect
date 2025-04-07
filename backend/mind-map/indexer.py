import numpy as np
import os
import json
import logging
import torch
import faiss
from typing import Dict, List, Any, Tuple, Optional
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MindMapIndexer:
    """
    Indexes and provides search capabilities for mind map content using FAISS.
    This enables efficient retrieval for paper generation based on relevance.
    """
    
    def __init__(self, index_dir: str = "indices"):
        """
        Initialize the indexer.
        
        Args:
            index_dir: Directory to store the FAISS indices
        """
        self.index_dir = index_dir
        os.makedirs(index_dir, exist_ok=True)
        logger.info(f"Initialized MindMapIndexer with index directory: {index_dir}")
    
    def create_index(self, indexed_mind_map: Dict[str, Any], session_id: str) -> str:
        """
        Create a FAISS index from the indexed mind map data.
        
        Args:
            indexed_mind_map: The indexed mind map with embeddings
            session_id: A unique session identifier
            
        Returns:
            Path to the saved index
        """
        try:
            # Extract embeddings from the indexed mind map
            embeddings = []
            ids = []
            contents = []
            
            # Process all node embeddings
            for node_id, node_data in indexed_mind_map["node_embeddings"].items():
                embeddings.append(node_data["embedding"])
                ids.append(node_id)
                contents.append(node_data["content"])
            
            # Create numpy array from embeddings
            embeddings_array = np.array(embeddings).astype('float32')
            dim = embeddings_array.shape[1]  # Dimensionality of embeddings
            
            # Create and train the index
            index = faiss.IndexFlatL2(dim)
            index.add(embeddings_array)
            
            # Save the index to disk
            index_path = os.path.join(self.index_dir, f"mind_map_index_{session_id}")
            faiss.write_index(index, index_path)
            
            # Save metadata for later retrieval
            metadata = {
                "ids": ids,
                "contents": contents,
                "session_id": session_id,
                "created_at": self._get_timestamp()
            }
            
            metadata_path = os.path.join(self.index_dir, f"mind_map_metadata_{session_id}.json")
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f)
            
            logger.info(f"Created FAISS index with {len(embeddings)} embeddings for session {session_id}")
            return index_path
        
        except Exception as e:
            logger.error(f"Error creating index: {e}")
            raise
    
    def search(self, 
              query_embedding: np.ndarray, 
              session_id: str, 
              k: int = 5) -> List[Dict[str, Any]]:
        """
        Search the index for relevant content based on a query embedding.
        
        Args:
            query_embedding: The embedding vector of the query
            session_id: The session identifier
            k: Number of results to return
            
        Returns:
            List of relevant content items with scores
        """
        try:
            # Load the index
            index_path = os.path.join(self.index_dir, f"mind_map_index_{session_id}")
            index = faiss.read_index(index_path)
            
            # Load metadata
            metadata_path = os.path.join(self.index_dir, f"mind_map_metadata_{session_id}.json")
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            
            # Perform the search
            query_embedding_array = np.array([query_embedding]).astype('float32')
            distances, indices = index.search(query_embedding_array, k)
            
            # Format results
            results = []
            for i, idx in enumerate(indices[0]):
                if idx >= 0 and idx < len(metadata["ids"]):
                    results.append({
                        "node_id": metadata["ids"][idx],
                        "content": metadata["contents"][idx],
                        "distance": float(distances[0][i]),
                        "score": 1.0 / (1.0 + float(distances[0][i]))  # Convert distance to similarity score
                    })
            
            logger.info(f"Found {len(results)} results for search in session {session_id}")
            return results
        
        except Exception as e:
            logger.error(f"Error searching index: {e}")
            raise
    
    def delete_index(self, session_id: str) -> bool:
        """
        Delete an index and its metadata.
        
        Args:
            session_id: The session identifier
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Delete the index file
            index_path = os.path.join(self.index_dir, f"mind_map_index_{session_id}")
            if os.path.exists(index_path):
                os.remove(index_path)
            
            # Delete the metadata file
            metadata_path = os.path.join(self.index_dir, f"mind_map_metadata_{session_id}.json")
            if os.path.exists(metadata_path):
                os.remove(metadata_path)
            
            logger.info(f"Deleted index for session {session_id}")
            return True
        
        except Exception as e:
            logger.error(f"Error deleting index: {e}")
            return False
    
    def list_indices(self) -> List[str]:
        """
        List all available indices.
        
        Returns:
            List of session IDs with indices
        """
        try:
            indices = []
            for file in os.listdir(self.index_dir):
                if file.startswith("mind_map_metadata_") and file.endswith(".json"):
                    session_id = file.replace("mind_map_metadata_", "").replace(".json", "")
                    indices.append(session_id)
            return indices
        
        except Exception as e:
            logger.error(f"Error listing indices: {e}")
            return []
    
    def _get_timestamp(self) -> str:
        """Get the current timestamp as a string."""
        from datetime import datetime
        return datetime.now().isoformat() 