"""
RAG (Retrieval Augmented Generation) module for background guide processing.

This module provides functions to index document segments using vector embeddings
and retrieve relevant context for queries to support RAG-based generation.
"""

import os
import json
import pickle
import numpy as np
from typing import Dict, List, Any, Tuple
import faiss
from sentence_transformers import SentenceTransformer

def create_vector_index(
    segments: List[Dict[str, Any]],
    embedding_model: SentenceTransformer,
    index_dir: str
) -> Dict[str, Any]:
    """
    Create a vector index from document segments for retrieval.
    
    Args:
        segments: List of document segments
        embedding_model: Model to use for generating embeddings
        index_dir: Directory to save the index files
        
    Returns:
        Dictionary with index information
    """
    os.makedirs(index_dir, exist_ok=True)
    
    # Extract texts to embed
    texts = []
    metadata = []
    
    for i, segment in enumerate(segments):
        # Skip segments with empty or very short text
        if not segment.get("text") or len(segment.get("text", "").split()) < 5:
            continue
            
        # Add the segment text
        texts.append(segment["text"])
        
        # Store metadata
        meta = {
            "id": i,
            "section": segment.get("section", ""),
            "subsection": segment.get("subsection"),
            "summary": segment.get("summary", ""),
            "level": segment.get("level", 1)
        }
        metadata.append(meta)
    
    # Generate embeddings
    print(f"Generating embeddings for {len(texts)} segments...")
    embeddings = embedding_model.encode(texts, show_progress_bar=True)
    
    # Convert to numpy array with float32 dtype for FAISS
    embeddings_np = np.array(embeddings).astype("float32")
    
    # Create and train the index
    dimension = embeddings_np.shape[1]
    index = faiss.IndexFlatL2(dimension)  # L2 distance index
    index.add(embeddings_np)
    
    # Save index, texts, and metadata
    faiss.write_index(index, os.path.join(index_dir, "vector.index"))
    
    with open(os.path.join(index_dir, "texts.json"), "w", encoding="utf-8") as f:
        json.dump(texts, f, ensure_ascii=False, indent=2)
        
    with open(os.path.join(index_dir, "metadata.json"), "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    
    # Return index info
    return {
        "directory": index_dir,
        "segments_count": len(texts),
        "dimension": dimension,
        "index_type": "FAISS IndexFlatL2"
    }

def retrieve_context(
    query: str,
    embed_model: SentenceTransformer,
    index_dir: str,
    top_k: int = 3
) -> List[Dict[str, Any]]:
    """
    Retrieve relevant context from a vector index for a given query.
    
    Args:
        query: The query to search for
        embed_model: Model to use for generating query embedding
        index_dir: Directory containing the FAISS index and metadata
        top_k: Number of top results to return
        
    Returns:
        List of relevant segments with text, section, and summary
    """
    # Load the index and metadata
    index_path = os.path.join(index_dir, "faiss_index.bin")
    metadata_path = os.path.join(index_dir, "metadata.pkl")
    
    if not os.path.exists(index_path) or not os.path.exists(metadata_path):
        print(f"Index or metadata not found in {index_dir}")
        return []
    
    try:
        # Load FAISS index
        index = faiss.read_index(index_path)
        
        # Load metadata
        with open(metadata_path, 'rb') as f:
            metadata = pickle.load(f)
        
        # Embed the query
        query_embedding = embed_model.encode([query])[0]
        query_embedding = np.array([query_embedding]).astype('float32')
        
        # Search the index
        distances, indices = index.search(query_embedding, top_k)
        
        # Prepare the results
        results = []
        for i, idx in enumerate(indices[0]):
            if idx != -1 and idx < len(metadata):  # -1 means no result
                # Get the segment metadata
                segment = metadata[idx]
                
                # Calculate relevance score (0-1 scale, lower distance = higher relevance)
                max_distance = 2.0  # Maximum possible distance (approx.)
                relevance = 1.0 - min(distances[0][i] / max_distance, 1.0)
                
                # Add result with relevance score
                result = {
                    "text": segment.get("text", ""),
                    "section": segment.get("section", "General"),
                    "summary": segment.get("summary", ""),
                    "score": float(relevance)
                }
                results.append(result)
        
        return results
    
    except Exception as e:
        print(f"Error retrieving context: {e}")
        return []

def provide_formatted_context(
    query: str,
    embed_model: SentenceTransformer,
    index_dir: str,
    top_k: int = 5
) -> Dict[str, Any]:
    """
    Provide RAG context in a standardized format for document generation
    
    Args:
        query: Query string for RAG retrieval
        embed_model: Model to use for embedding
        index_dir: Directory containing the FAISS index
        top_k: Number of results to return
        
    Returns:
        Formatted context for document generation
    """
    try:
        # Retrieve context using existing RAG functionality
        contexts = retrieve_context(query, embed_model, index_dir, top_k)
        
        # Format for document generator
        rag_context = {
            "sections": [
                {
                    "section": ctx.get("section", "General"),
                    "text": ctx.get("text", ""),
                    "summary": ctx.get("summary", ""),
                    "relevance": ctx.get("score", 1.0)
                }
                for ctx in contexts
            ],
            "query": query,
            "metadata": {
                "index_dir": index_dir,
                "top_k": top_k,
                "timestamp": import_datetime_and_get_timestamp()
            }
        }
        
        return rag_context
        
    except Exception as e:
        print(f"Error providing formatted context: {e}")
        # Return empty but valid structure
        return {
            "sections": [],
            "query": query,
            "metadata": {
                "error": str(e),
                "timestamp": import_datetime_and_get_timestamp()
            }
        }

def import_datetime_and_get_timestamp():
    """Import datetime and get current timestamp to avoid circular imports"""
    from datetime import datetime
    return datetime.now().isoformat()

def search_topic_files(
    query: str,
    embedding_model: SentenceTransformer,
    topics_dir: str,
    top_k: int = 3
) -> List[Dict[str, Any]]:
    """
    Search topic files for relevant information.
    
    Args:
        query: Query to search for
        embedding_model: Model to use for generating query embedding
        topics_dir: Directory with topic JSON files
        top_k: Number of top results to return
        
    Returns:
        List of relevant topic segments
    """
    # Generate query embedding
    query_embedding = embedding_model.encode([query])[0]
    
    # Find and load all topic files
    all_segments = []
    for filename in os.listdir(topics_dir):
        if not filename.endswith(".json"):
            continue
            
        filepath = os.path.join(topics_dir, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                topic_data = json.load(f)
                
            topic = topic_data.get("topic", "Unknown")
            segments = topic_data.get("segments", [])
            
            # Add topic info to each segment
            for segment in segments:
                segment["topic"] = topic
                all_segments.append(segment)
                
        except Exception as e:
            print(f"Error loading topic file {filepath}: {e}")
    
    # If no segments found, return empty list
    if not all_segments:
        return []
    
    # Generate embeddings for all segments
    texts = [segment.get("text", "") for segment in all_segments]
    embeddings = embedding_model.encode(texts)
    
    # Calculate similarity scores
    similarities = []
    for i, embedding in enumerate(embeddings):
        # Calculate cosine similarity
        similarity = np.dot(query_embedding, embedding) / (
            np.linalg.norm(query_embedding) * np.linalg.norm(embedding)
        )
        similarities.append((similarity, i))
    
    # Sort by similarity (descending)
    similarities.sort(reverse=True)
    
    # Return top-k results
    results = []
    for similarity, idx in similarities[:top_k]:
        result = {
            "text": all_segments[idx].get("text", ""),
            "score": float(similarity),
            "topic": all_segments[idx].get("topic", ""),
            "section": all_segments[idx].get("section", ""),
            "subsection": all_segments[idx].get("subsection"),
            "summary": all_segments[idx].get("summary", "")
        }
        results.append(result)
    
    return results

def build_rag_context(query: str, results: List[Dict[str, Any]]) -> str:
    """
    Build a formatted context string for RAG from search results.
    
    Args:
        query: Original query
        results: List of search results
        
    Returns:
        Formatted context string
    """
    context = f"QUERY: {query}\n\nRELEVANT CONTEXT:\n\n"
    
    for i, result in enumerate(results, 1):
        context += f"SEGMENT {i}:\n"
        if "topic" in result:
            context += f"TOPIC: {result['topic']}\n"
        if "section" in result:
            context += f"SECTION: {result['section']}\n"
        if "subsection" in result and result["subsection"]:
            context += f"SUBSECTION: {result['subsection']}\n"
        
        context += f"TEXT: {result['text']}\n"
        
        if "summary" in result and result["summary"]:
            context += f"SUMMARY: {result['summary']}\n"
            
        context += "\n---\n\n"
    
    return context 