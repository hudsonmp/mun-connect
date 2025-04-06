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
    embedding_model: SentenceTransformer,
    index_dir: str,
    top_k: int = 3
) -> List[Dict[str, Any]]:
    """
    Retrieve relevant context for a query using the vector index.
    
    Args:
        query: Query to search for
        embedding_model: Model to use for generating query embedding
        index_dir: Directory with index files
        top_k: Number of top results to return
        
    Returns:
        List of relevant segments with text and metadata
    """
    # Check if index exists
    index_path = os.path.join(index_dir, "vector.index")
    texts_path = os.path.join(index_dir, "texts.json")
    metadata_path = os.path.join(index_dir, "metadata.json")
    
    if not os.path.exists(index_path) or not os.path.exists(texts_path) or not os.path.exists(metadata_path):
        raise FileNotFoundError(f"Index files not found in {index_dir}")
    
    # Load index
    index = faiss.read_index(index_path)
    
    # Load texts and metadata
    with open(texts_path, "r", encoding="utf-8") as f:
        texts = json.load(f)
        
    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)
    
    # Generate query embedding
    query_embedding = embedding_model.encode([query])[0].astype("float32")
    query_embedding = query_embedding.reshape(1, -1)
    
    # Search the index
    distances, indices = index.search(query_embedding, top_k)
    
    # Format results
    results = []
    for i, idx in enumerate(indices[0]):
        if idx < 0 or idx >= len(texts):
            continue  # Skip invalid indices
            
        result = {
            "text": texts[idx],
            "distance": float(distances[0][i]),
            "score": 1.0 / (1.0 + float(distances[0][i])),  # Convert distance to similarity score
            **metadata[idx]  # Add all metadata
        }
        results.append(result)
    
    return results

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