"""
Background Guide Processor

This module provides functionality to process PDF and text input files,
extract content, segment text, analyze and summarize content, and generate
structured JSON outputs. It uses a combination of local processing and
cloud-based AI services (OpenAI API and AWS hosted models).
"""

import os
import json
import re
from typing import Dict, List, Optional, Tuple, Union, Any
import torch
from torch import Tensor
import numpy as np
from urllib.parse import urljoin
import requests
from pathlib import Path
from datetime import datetime

# File processing
import fitz  # PyMuPDF

# ML models
from transformers import (
    AutoTokenizer, 
    AutoModelForSequenceClassification,
    AutoModelForSeq2SeqLM,
    pipeline
)
from sentence_transformers import SentenceTransformer
import faiss

# Custom modules
from .extraction import extract_text_from_pdf, clean_text
from .segmentation import segment_document
from .summary import summarize_content
from .json_generator import generate_json_outputs
from .rag import create_vector_index, retrieve_context

# Constants for model paths and API endpoints
DEFAULT_MODELS = {
    "segmentation": "distilbert-base-uncased-finetuned-sst-2-english",  # Placeholder, should use appropriate model
    "summarization": "facebook/bart-large-cnn",
    "embedding": "sentence-transformers/all-MiniLM-L6-v2"
}

AWS_ENDPOINT = os.environ.get("AWS_MODEL_ENDPOINT", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

class BackgroundGuideProcessor:
    """
    Main processor class for handling background guide documents.
    
    This class orchestrates the entire processing pipeline from file ingestion
    to JSON generation and RAG preparation.
    """
    
    def __init__(
        self,
        segmentation_model: Optional[str] = None,
        summarization_model: Optional[str] = None,
        embedding_model: Optional[str] = None,
        use_openai_for_summary: bool = True,
        use_aws_model: bool = True,
        output_dir: Optional[str] = None
    ):
        """
        Initialize the background guide processor.
        
        Args:
            segmentation_model: Model to use for text segmentation
            summarization_model: Model to use for text summarization
            embedding_model: Model to use for generating embeddings
            use_openai_for_summary: Whether to use OpenAI API for summarization
            use_aws_model: Whether to use AWS hosted model for refinement
            output_dir: Directory to store output JSON files
        """
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Using device: {self.device}")
        
        # Initialize models
        self.segmentation_model = segmentation_model or DEFAULT_MODELS["segmentation"]
        self.summarization_model = summarization_model or DEFAULT_MODELS["summarization"]
        self.embedding_model = embedding_model or DEFAULT_MODELS["embedding"]
        
        self.use_openai_for_summary = use_openai_for_summary
        self.use_aws_model = use_aws_model
        
        # Create output directory if needed
        self.output_dir = output_dir or "output"
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Load models
        self._load_models()
        
    def _load_models(self):
        """Load all required models for processing."""
        if not self.use_openai_for_summary:
            print(f"Loading summarization model: {self.summarization_model}")
            self.summarizer = pipeline(
                "summarization", 
                model=self.summarization_model,
                device=0 if self.device == "cuda" else -1
            )
        
        print(f"Loading embedding model: {self.embedding_model}")
        self.embed_model = SentenceTransformer(self.embedding_model, device=self.device)
        
        # Segmentation model is loaded on demand
        self.segment_tokenizer = None
        self.segment_model = None
    
    def _load_segmentation_model(self):
        """Load the segmentation model if not already loaded."""
        if self.segment_model is None:
            print(f"Loading segmentation model: {self.segmentation_model}")
            self.segment_tokenizer = AutoTokenizer.from_pretrained(self.segmentation_model)
            self.segment_model = AutoModelForSequenceClassification.from_pretrained(
                self.segmentation_model
            ).to(self.device)
    
    def process_file(self, file_path: str) -> Dict[str, Any]:
        """
        Process a file (PDF or text) to extract and analyze its content.
        
        Args:
            file_path: Path to the file to process
            
        Returns:
            A dictionary containing the processing results in standardized format
        """
        print(f"Processing file: {file_path}")
        
        # Store filename and file path for later use
        self.file_name = os.path.basename(file_path)
        self.file_path = file_path
        
        # Extract text from file
        if file_path.lower().endswith('.pdf'):
            text = extract_text_from_pdf(file_path)
        else:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
        
        # Clean the text
        cleaned_text = clean_text(text)
        
        # Segment the document
        segments = segment_document(cleaned_text, self.segment_tokenizer, self.segment_model)
        self.segments = segments
        
        # Summarize each segment
        summaries = []
        for segment in segments:
            summary = summarize_content(
                segment["text"], 
                use_openai=self.use_openai_for_summary,
                summarizer=self.summarizer if not self.use_openai_for_summary else None
            )
            segment["summary"] = summary
            summaries.append(summary)
        self.summaries = summaries
        
        # Generate JSON outputs
        json_files = generate_json_outputs(
            segments, 
            self.output_dir, 
            use_aws_model=self.use_aws_model,
            aws_endpoint=AWS_ENDPOINT
        )
        
        # Create vector index for RAG
        index_info = create_vector_index(
            segments, 
            self.embed_model, 
            os.path.join(self.output_dir, "index")
        )
        self.index_info = index_info
        
        # Return standardized output
        return self.get_standardized_output()
    
    def get_standardized_output(self) -> Dict[str, Any]:
        """
        Return processor results in the standard integration format.
        
        This method should be called after process_file() to get results
        in a format that can be directly used by other modules.
        
        Returns:
            A dictionary containing standardized output with metadata, 
            segments, summaries, and index information.
        """
        if not hasattr(self, 'segments') or not hasattr(self, 'summaries'):
            raise RuntimeError("Must call process_file() before get_standardized_output()")
            
        # Extract committee and topic info from segments if available
        committee = self._extract_committee_info()
        topic = self._extract_topic_info()
        
        return {
            "metadata": {
                "title": getattr(self, 'file_name', 'unknown'),
                "committee": committee,
                "topic": topic,
                "created_at": datetime.now().isoformat()
            },
            "segments": self.segments,
            "summaries": {
                "executive_summary": self._generate_executive_summary(),
                "topic_summary": self.summaries[0] if self.summaries else "",
                "subtopic_summaries": {f"section_{i}": summary for i, summary in enumerate(self.summaries[1:])}
            },
            "index_info": getattr(self, 'index_info', {})
        }
    
    def _extract_committee_info(self) -> str:
        """
        Extract committee information from segments.
        
        Returns:
            Committee name or default value
        """
        # Simple extraction logic - look for committee name in first segment
        if hasattr(self, 'segments') and self.segments:
            first_segment = self.segments[0]["text"]
            # Look for patterns like "DISEC", "Security Council", etc.
            committee_patterns = [
                r"(?:Committee|Council|Commission)[\s:]+([A-Za-z\s]+)",
                r"([A-Z]{3,})\s+(?:Committee|Council)"
            ]
            for pattern in committee_patterns:
                match = re.search(pattern, first_segment)
                if match:
                    return match.group(1).strip()
        
        return "General Assembly" # Default value
    
    def _extract_topic_info(self) -> str:
        """
        Extract topic information from segments.
        
        Returns:
            Topic or default value
        """
        # Simple extraction logic - look for topic indicators in first segments
        if hasattr(self, 'segments') and self.segments:
            # Check first two segments for topic indicators
            text = self.segments[0]["text"]
            if len(self.segments) > 1:
                text += " " + self.segments[1]["text"]
                
            # Look for patterns like "Topic: X", "Agenda Item: X"
            topic_patterns = [
                r"Topic[\s:]+([^\n.]+)",
                r"Agenda[\s:]+([^\n.]+)",
                r"Subject[\s:]+([^\n.]+)"
            ]
            for pattern in topic_patterns:
                match = re.search(pattern, text)
                if match:
                    return match.group(1).strip()
        
        return "General Debate" # Default value
    
    def _generate_executive_summary(self) -> str:
        """
        Generate an executive summary from all segment summaries.
        
        Returns:
            Executive summary text
        """
        if not hasattr(self, 'summaries') or not self.summaries:
            return ""
            
        # Combine all summaries and generate an executive summary
        combined_summary = " ".join(self.summaries)
        
        # If OpenAI is available, use it to create a concise executive summary
        if self.use_openai_for_summary:
            import openai
            
            # Set OpenAI API key
            openai.api_key = OPENAI_API_KEY
            
            try:
                response = openai.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are an expert at creating concise executive summaries."},
                        {"role": "user", "content": f"Create a concise executive summary (150 words max) of this background guide:\n\n{combined_summary}"}
                    ],
                    temperature=0.7,
                    max_tokens=200
                )
                return response.choices[0].message.content
            except Exception as e:
                print(f"Error generating executive summary with OpenAI: {e}")
                return combined_summary[:500] + "..."
        else:
            # Simple approach: use the first summary as the executive summary
            return self.summaries[0] if self.summaries else ""
    
    def retrieve_context_for_query(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Retrieve relevant context for a given query using the vector index.
        
        Args:
            query: The query to search for context
            top_k: Number of top results to return
            
        Returns:
            List of relevant context segments
        """
        return retrieve_context(
            query, 
            self.embed_model, 
            os.path.join(self.output_dir, "index"),
            top_k
        )
    
    def generate_custom_guide(self, query: str, openai_model: str = "gpt-4o-mini") -> str:
        """
        Generate a custom background guide for a given query using RAG.
        
        Args:
            query: The query to generate a guide for
            openai_model: The OpenAI model to use
            
        Returns:
            Generated custom background guide text
        """
        import openai
        
        # Set OpenAI API key
        openai.api_key = OPENAI_API_KEY
        
        # Retrieve context for query
        context = self.retrieve_context_for_query(query)
        
        # Format context for the prompt
        context_text = "\n\n".join([
            f"SECTION: {ctx['section']}\n{ctx['text']}\nSUMMARY: {ctx['summary']}"
            for ctx in context
        ])
        
        # Create prompt
        prompt = f"""
        Create a custom background guide based on the following query:
        
        QUERY: {query}
        
        Here is relevant context from the original background guide:
        
        {context_text}
        
        Create a comprehensive background guide that answers the query, using the provided 
        context as a foundation but enriching it with additional research and details.
        """
        
        # Call OpenAI API
        response = openai.chat.completions.create(
            model=openai_model,
            messages=[
                {"role": "system", "content": "You are an expert researcher who creates detailed and informative background guides for Model United Nations conferences."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        return response.choices[0].message.content 