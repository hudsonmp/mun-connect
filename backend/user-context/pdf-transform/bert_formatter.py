#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
BERT Formatter Module

This module formats document data for optimal processing with BERT-based models.
It segments text to fit token limits, adds structural markers, and pre-computes
linguistic features to aid in analysis.

Optimized for AWS Lambda with S3 integration and tokenizer caching.
"""

import re
import os
import json
import time
import logging
import math
from typing import Dict, List, Any, Optional, Tuple, Union
from functools import lru_cache

# AWS imports
import boto3
import botocore
from botocore.exceptions import ClientError

# ML imports
import nltk
import textstat
import numpy as np

# Import PyTorch conditionally for Lambda optimization
try:
    import torch
    from transformers import AutoTokenizer, AutoModel
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logging.warning("PyTorch not found. Document embedding functionality will be limited.")

# Configure logging for CloudWatch
log_level = os.environ.get('LOG_LEVEL', 'INFO')
numeric_level = getattr(logging, log_level.upper(), None)
if not isinstance(numeric_level, int):
    numeric_level = logging.INFO

logging.basicConfig(
    level=numeric_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize S3 client
try:
    s3_client = boto3.client('s3')
    logger.info("Initialized S3 client")
except Exception as e:
    logger.error(f"Failed to initialize S3 client: {e}")
    s3_client = None

# CloudWatch metrics client
try:
    cloudwatch_client = boto3.client('cloudwatch')
    logger.info("Initialized CloudWatch client")
except Exception as e:
    logger.warning(f"Failed to initialize CloudWatch client: {e}")
    cloudwatch_client = None

# Environment settings
USE_S3 = os.environ.get('USE_S3', 'true').lower() == 'true'
S3_BUCKET = os.environ.get('S3_BUCKET', 'doc-processor-dev')
TEST_ENV = os.environ.get('TEST_ENV', 'false').lower() == 'true'
EFS_MOUNT_PATH = '/mnt/efs' if os.path.exists('/mnt/efs') else None
MODEL_CACHE_DIR = os.path.join(EFS_MOUNT_PATH, 'models') if EFS_MOUNT_PATH else None
MEMORY_LIMIT_MB = int(os.environ.get('MEMORY_LIMIT_MB', '0'))

# Set up tokenizer model configuration for different environments
TOKENIZER_CONFIG = {
    "production": {
        "default": "bert-base-uncased",
        "small": "distilbert-base-uncased",
        "multilingual": "bert-base-multilingual-cased"
    },
    "test": {
        "default": "distilbert-base-uncased",
        "small": "distilbert-base-uncased",
        "multilingual": "distilbert-base-multilingual-cased"
    }
}

# Global tokenizer cache to avoid reloading
_tokenizer_cache = {}

# Ensure NLTK resources are available
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    # For Lambda, download to a writable location
    nltk_data_path = os.environ.get('NLTK_DATA', '/tmp/nltk_data')
    if not os.path.exists(nltk_data_path):
        os.makedirs(nltk_data_path, exist_ok=True)
    os.environ['NLTK_DATA'] = nltk_data_path
    nltk.download('punkt', download_dir=nltk_data_path, quiet=True)

# S3 utility functions
def save_to_s3(data: Union[Dict, List, str], s3_key: str, content_type: str = 'application/json') -> str:
    """
    Save data to S3.
    
    Args:
        data: Data to save (dict/list will be converted to JSON)
        s3_key: S3 object key
        content_type: Content type of the data
        
    Returns:
        S3 URI
    """
    if not USE_S3 or s3_client is None:
        return None
    
    try:
        # Convert to JSON if dict or list
        if isinstance(data, (dict, list)):
            body = json.dumps(data, indent=2)
        else:
            body = data
            
        s3_client.put_object(
            Body=body,
            Bucket=S3_BUCKET,
            Key=s3_key,
            ContentType=content_type
        )
        logger.info(f"Saved data to s3://{S3_BUCKET}/{s3_key}")
        return f"s3://{S3_BUCKET}/{s3_key}"
    except ClientError as e:
        logger.error(f"Error saving to S3: {e}", exc_info=True)
        return None

def load_from_s3(s3_key: str) -> Union[Dict, List, str, None]:
    """
    Load data from S3.
    
    Args:
        s3_key: S3 object key
        
    Returns:
        Loaded data (automatically parsed if JSON)
    """
    if not USE_S3 or s3_client is None:
        return None
    
    try:
        response = s3_client.get_object(Bucket=S3_BUCKET, Key=s3_key)
        content_type = response.get('ContentType', '')
        data = response['Body'].read()
        
        # Auto-parse JSON
        if 'json' in content_type or s3_key.endswith('.json'):
            return json.loads(data.decode('utf-8'))
        return data
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchKey':
            logger.warning(f"Object not found in S3: {s3_key}")
        else:
            logger.error(f"Error loading from S3: {e}", exc_info=True)
        return None

def put_cloudwatch_metric(name: str, value: float, unit: str = 'Milliseconds', namespace: str = 'BertFormatter'):
    """
    Put a metric to CloudWatch.
    
    Args:
        name: Metric name
        value: Metric value
        unit: Metric unit
        namespace: Metric namespace
    """
    if cloudwatch_client is None:
        return
    
    try:
        cloudwatch_client.put_metric_data(
            Namespace=namespace,
            MetricData=[
                {
                    'MetricName': name,
                    'Value': value,
                    'Unit': unit
                }
            ]
        )
        logger.debug(f"Put metric {name}={value} {unit} to CloudWatch")
    except Exception as e:
        logger.warning(f"Failed to put CloudWatch metric: {e}")

# Timing decorator for tracking function performance
def timed_execution(func):
    """Decorator to time function execution and send metric to CloudWatch"""
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            execution_time = (time.time() - start_time) * 1000  # Convert to ms
            function_name = func.__name__
            logger.debug(f"{function_name} executed in {execution_time:.2f}ms")
            put_cloudwatch_metric(function_name, execution_time)
    return wrapper

# Load tokenizer with caching
@lru_cache(maxsize=4)
def get_tokenizer(model_name: str) -> Any:
    """
    Get a tokenizer with caching.
    
    Args:
        model_name: Name of the tokenizer model
        
    Returns:
        Tokenizer instance
    """
    global _tokenizer_cache
    
    # Check if already in memory cache
    if model_name in _tokenizer_cache:
        logger.debug(f"Using in-memory cached tokenizer for {model_name}")
        return _tokenizer_cache[model_name]
    
    # Check if we have a cached version in S3
    if USE_S3:
        s3_cache_key = f"tokenizers/{model_name}/config.json"
        cache_exists = False
        
        try:
            # Check if tokenizer exists in S3
            s3_client.head_object(Bucket=S3_BUCKET, Key=s3_cache_key)
            cache_exists = True
        except:
            cache_exists = False
            
        if cache_exists:
            try:
                # Use local temp dir for downloading
                cache_dir = '/tmp/transformers_cache'
                os.makedirs(cache_dir, exist_ok=True)
                
                logger.info(f"Loading tokenizer {model_name} from S3 cache")
                tokenizer = AutoTokenizer.from_pretrained(
                    f"s3://{S3_BUCKET}/tokenizers/{model_name}/",
                    local_files_only=False,
                    cache_dir=cache_dir
                )
                _tokenizer_cache[model_name] = tokenizer
                return tokenizer
            except Exception as e:
                logger.warning(f"Failed to load tokenizer from S3 cache: {e}")
                # Fall back to loading from Hugging Face
    
    # No cache, load from Hugging Face
    start_time = time.time()
    try:
        # If in test mode with memory constraints, use smaller tokenizer
        if TEST_ENV and MEMORY_LIMIT_MB > 0:
            # Use local temp dir for downloading
            cache_dir = '/tmp/transformers_cache'
            os.makedirs(cache_dir, exist_ok=True)
            
            # Set up a more memory-efficient tokenizer configuration  
            tokenizer = AutoTokenizer.from_pretrained(
                model_name,
                cache_dir=cache_dir,
                local_files_only=False,
                use_fast=True  # Use the faster Rust-based tokenizer implementation
            )
        else:
            # For production or unconstrained testing, use EFS cache if available
            cache_dir = MODEL_CACHE_DIR if MODEL_CACHE_DIR else None
            tokenizer = AutoTokenizer.from_pretrained(
                model_name,
                cache_dir=cache_dir
            )
        
        # Cache the tokenizer in memory
        _tokenizer_cache[model_name] = tokenizer
        
        # Save to S3 for future use if enabled
        if USE_S3:
            try:
                local_path = tokenizer.save_pretrained('/tmp/tokenizer_save')
                
                # Upload files to S3
                for root, _, files in os.walk('/tmp/tokenizer_save'):
                    for file in files:
                        local_file_path = os.path.join(root, file)
                        s3_path = f"tokenizers/{model_name}/{file}"
                        with open(local_file_path, 'rb') as f:
                            s3_client.put_object(
                                Body=f.read(),
                                Bucket=S3_BUCKET,
                                Key=s3_path,
                                ContentType='application/octet-stream'
                            )
                logger.info(f"Cached tokenizer {model_name} to S3")
            except Exception as e:
                logger.warning(f"Failed to cache tokenizer to S3: {e}")
        
        load_time = time.time() - start_time
        put_cloudwatch_metric("TokenizerLoadTime", load_time * 1000)
        logger.info(f"Loaded tokenizer {model_name} in {load_time:.2f} seconds")
        
        return tokenizer
    except Exception as e:
        logger.error(f"Error loading tokenizer {model_name}: {e}", exc_info=True)
        
        # In test mode, create a simple mock tokenizer
        if TEST_ENV:
            logger.info("Creating mock tokenizer for test environment")
            return create_mock_tokenizer()
        raise

def create_mock_tokenizer():
    """Create a simple mock tokenizer for testing"""
    class MockTokenizer:
        def __init__(self):
            self.vocab_size = 1000
            
        def encode(self, text, add_special_tokens=True, **kwargs):
            # Very simple encoding - just count the words and assign sequential IDs
            words = text.split()
            if add_special_tokens:
                return [101] + [i % 1000 + 1 for i in range(len(words))] + [102]
            return [i % 1000 + 1 for i in range(len(words))]
            
        def decode(self, token_ids, **kwargs):
            # For decoding, just return a placeholder text of the right length
            content_tokens = [t for t in token_ids if t not in (101, 102)]
            return ' '.join(['word'] * len(content_tokens))
            
        def __call__(self, text, add_special_tokens=True, **kwargs):
            ids = self.encode(text, add_special_tokens=add_special_tokens)
            return {
                "input_ids": ids,
                "token_type_ids": [0] * len(ids),
                "attention_mask": [1] * len(ids)
            }
            
        def save_pretrained(self, path):
            os.makedirs(path, exist_ok=True)
            with open(os.path.join(path, 'config.json'), 'w') as f:
                json.dump({"model_type": "mock", "vocab_size": self.vocab_size}, f)
            return path
            
    return MockTokenizer()

class BertFormatter:
    """Class for formatting document data for BERT processing"""
    
    # Class-level shared instance
    _instance = None
    
    @classmethod
    def get_instance(cls, **kwargs):
        """Get a singleton instance of the formatter"""
        if cls._instance is None:
            cls._instance = cls(**kwargs)
        return cls._instance
    
    def __init__(
        self, 
        model_name: str = None,
        variant: str = "default",
        use_s3: bool = None,
        memory_limit: int = None
    ):
        """
        Initialize the BERT formatter.
        
        Args:
            model_name: Name of the BERT model to use for tokenization
            variant: Model variant to use ('default', 'small', 'multilingual')
            use_s3: Whether to use S3 for storage
            memory_limit: Memory limit for the model in MB (for testing)
        """
        # Configure settings
        self.use_s3 = use_s3 if use_s3 is not None else USE_S3
        self.memory_limit = memory_limit or MEMORY_LIMIT_MB
        
        # Select model based on environment
        env = "test" if TEST_ENV else "production"
        self.model_name = model_name or TOKENIZER_CONFIG[env][variant]
        
        try:
            # Initialize tokenizer
            self.tokenizer = get_tokenizer(self.model_name)
            logger.info(f"Loaded tokenizer for {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to load tokenizer: {e}")
            
            if TEST_ENV:
                logger.info("Creating mock tokenizer for test environment")
                self.tokenizer = create_mock_tokenizer()
            else:
                raise
    
    @timed_execution
    def format_for_bert(self, document_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format document data for BERT processing.
        
        Args:
            document_data: Document data dictionary
            
        Returns:
            Document data formatted for BERT processing
        """
        start_time = time.time()
        
        # Ensure the bert_friendly object exists
        if "bert_friendly" not in document_data:
            document_data["bert_friendly"] = {}
            
        # Ensure the features object exists
        if "features" not in document_data:
            document_data["features"] = {}
            
        # Add segment information
        document_data = self.segment_document(document_data)
        
        # Add structure markers
        document_data = self.add_structure_markers(document_data)
        
        # Add linguistic features
        document_data = self.add_linguistic_features(document_data)
        
        # Add embedding for the document only if PyTorch is available
        if TORCH_AVAILABLE and not TEST_ENV:
            document_data = self.add_document_embedding(document_data)
            
        # Save formatted data to S3 if enabled
        if self.use_s3 and "file_id" in document_data.get("metadata", {}):
            file_id = document_data["metadata"]["file_id"]
            s3_key = f"document_processing/{file_id}/bert_formatted.json"
            save_to_s3(document_data, s3_key)
        
        # Record performance metrics
        total_time = time.time() - start_time
        put_cloudwatch_metric("TotalFormattingTime", total_time * 1000)
        
        # Report memory usage for monitoring
        if TORCH_AVAILABLE:
            try:
                if torch.cuda.is_available():
                    mem_allocated = torch.cuda.memory_allocated() / (1024 ** 2)  # MB
                    mem_reserved = torch.cuda.memory_reserved() / (1024 ** 2)    # MB
                    put_cloudwatch_metric("GpuMemoryAllocated", mem_allocated, "Megabytes")
                    put_cloudwatch_metric("GpuMemoryReserved", mem_reserved, "Megabytes")
            except Exception as e:
                logger.warning(f"Error recording GPU memory metrics: {e}")
        
        return document_data
    
    @timed_execution
    def segment_document(self, document_data: Dict[str, Any], max_length: int = 512, overlap: int = 50) -> Dict[str, Any]:
        """
        Segment document into BERT-friendly chunks.
        
        Args:
            document_data: Document data dictionary
            max_length: Maximum sequence length for BERT
            overlap: Number of tokens to overlap between segments
            
        Returns:
            Document data with segment information added
        """
        # Handle S3-stored content if needed
        if self.use_s3 and "s3_references" in document_data:
            if "full_text" in document_data["s3_references"].get("content", {}):
                s3_key = document_data["s3_references"]["content"]["full_text"]
                text_content = load_from_s3(s3_key)
                if text_content is not None:
                    document_data["content"]["full_text"] = text_content
                
            if "paragraphs" in document_data["s3_references"].get("content", {}):
                s3_key = document_data["s3_references"]["content"]["paragraphs"]
                paragraphs = load_from_s3(s3_key)
                if paragraphs is not None:
                    document_data["content"]["paragraphs"] = paragraphs
        
        # Now proceed with segmentation
        text = document_data["content"].get("full_text", "")
        paragraphs = document_data["content"].get("paragraphs", [])
        
        # If no text or paragraphs, return document data unchanged
        if not text and not paragraphs:
            logger.warning("No text or paragraphs to segment")
            document_data["bert_friendly"]["segments"] = []
            document_data["bert_friendly"]["segment_count"] = 0
            document_data["bert_friendly"]["token_count"] = 0
            return document_data
            
        # Create segments by processing paragraphs
        segments = []
        current_segment = ""
        current_tokens = []
        token_count = 0
        
        # Set a smaller batch size for memory constrained environments
        batch_size = 16 if not self.memory_limit else 8
        
        # Process paragraphs in batches for better memory management
        for i in range(0, len(paragraphs), batch_size):
            batch_paragraphs = paragraphs[i:i+batch_size]
            
            # In memory constrained environments, clear the cache periodically
            if TEST_ENV and self.memory_limit and i > 0 and i % 32 == 0:
                # Force garbage collection and clear token cache
                if TORCH_AVAILABLE and hasattr(torch, "cuda") and torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    
                # Log memory usage for debugging
                import resource
                mem_usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024  # MB
                logger.debug(f"Memory usage: {mem_usage:.2f} MB")
                put_cloudwatch_metric("MemoryUsage", mem_usage, "Megabytes")
            
            for para in batch_paragraphs:
                # Skip empty paragraphs
                if not para.strip():
                    continue
                    
                # Tokenize paragraph
                para_tokens = self.tokenizer.encode(para, add_special_tokens=False)
                
                # Check if adding this paragraph would exceed the limit
                if token_count + len(para_tokens) > max_length - 2:  # -2 for [CLS] and [SEP]
                    if current_segment:
                        # Add current segment to the list
                        segments.append({
                            "text": current_segment.strip(),
                            "tokens": len(current_tokens) + 2,  # +2 for [CLS] and [SEP]
                            "paragraphs": current_segment.count("\n\n") + 1
                        })
                    
                    # Start a new segment, possibly with overlap
                    if overlap > 0 and current_tokens:
                        # Calculate how many tokens to keep for overlap
                        overlap_tokens = min(overlap, len(current_tokens))
                        
                        # Get text representation of overlapping tokens
                        overlap_text = self.tokenizer.decode(current_tokens[-overlap_tokens:])
                        
                        # Start new segment with overlap
                        current_segment = overlap_text + "\n\n" + para
                        current_tokens = current_tokens[-overlap_tokens:] + para_tokens
                        token_count = len(current_tokens)
                    else:
                        # Start fresh with no overlap
                        current_segment = para
                        current_tokens = para_tokens
                        token_count = len(para_tokens)
                else:
                    # Add paragraph to current segment
                    if current_segment:
                        current_segment += "\n\n" + para
                    else:
                        current_segment = para
                    current_tokens.extend(para_tokens)
                    token_count += len(para_tokens)
        
        # Add the last segment if it exists
        if current_segment:
            segments.append({
                "text": current_segment.strip(),
                "tokens": len(current_tokens) + 2,  # +2 for [CLS] and [SEP]
                "paragraphs": current_segment.count("\n\n") + 1
            })
        
        # Update document data
        document_data["bert_friendly"]["segments"] = segments
        document_data["bert_friendly"]["segment_count"] = len(segments)
        document_data["bert_friendly"]["token_count"] = sum(seg["tokens"] for seg in segments)
        
        # Alternative segmentation approach - character-based chunks with sentence boundaries preserved
        sentences = document_data["content"].get("sentences", [])
        if sentences:
            document_data["bert_friendly"]["alternative_segments"] = self._create_alternative_segments(
                sentences, max_length
            )
        
        # Store segments to S3 if enabled and they're large
        if self.use_s3 and "file_id" in document_data.get("metadata", {}) and len(segments) > 10:
            file_id = document_data["metadata"]["file_id"]
            s3_key = f"document_processing/{file_id}/segments.json"
            segments_data = {
                "segments": segments,
                "segment_count": len(segments),
                "token_count": sum(seg["tokens"] for seg in segments)
            }
            s3_uri = save_to_s3(segments_data, s3_key)
            
            if s3_uri:
                # Replace segments with S3 reference
                document_data["bert_friendly"]["segments"] = "See S3 reference"
                document_data["bert_friendly"]["s3_reference_segments"] = s3_uri
        
        return document_data
    
    @timed_execution
    def add_structure_markers(self, document_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add special markers to denote document structure.
        
        Args:
            document_data: Document data dictionary
            
        Returns:
            Document data with structure markers added
        """
        # Define markers for document structure
        SECTION_START = "[SECTION]"
        PARAGRAPH_START = "[PARA]"
        ARGUMENT_START = "[ARG]"
        CLAIM_START = "[CLAIM]"
        EVIDENCE_START = "[EVIDENCE]"
        CONCLUSION_START = "[CONCLUSION]"
        
        # Get text from document data or S3
        text = document_data["content"].get("full_text", "")
        if not text and self.use_s3 and "s3_references" in document_data:
            if "full_text" in document_data["s3_references"].get("content", {}):
                s3_key = document_data["s3_references"]["content"]["full_text"]
                text_content = load_from_s3(s3_key)
                if text_content is not None:
                    text = text_content
                    document_data["content"]["full_text"] = text
        
        marked_text = text
        
        # Mark sections if available
        if "sections" in document_data["content"] and document_data["content"]["sections"]:
            for section in document_data["content"]["sections"]:
                if "title" in section and section["title"] and section["title"] in text:
                    # Add section marker before section title
                    marked_text = marked_text.replace(
                        section["title"],
                        f"{SECTION_START} {section['title']}"
                    )
        
        # Mark paragraphs
        paragraphs = document_data["content"].get("paragraphs", [])
        if not paragraphs and self.use_s3 and "s3_references" in document_data:
            if "paragraphs" in document_data["s3_references"].get("content", {}):
                s3_key = document_data["s3_references"]["content"]["paragraphs"]
                paragraphs_data = load_from_s3(s3_key)
                if paragraphs_data is not None:
                    paragraphs = paragraphs_data
                    document_data["content"]["paragraphs"] = paragraphs
        
        for para in paragraphs:
            if para in marked_text:
                # Add paragraph marker to the beginning of each paragraph
                marked_text = marked_text.replace(
                    para,
                    f"{PARAGRAPH_START} {para}"
                )
        
        # Use rule-based patterns to identify argument components
        marked_text = self._mark_argument_components(marked_text)
        
        # Store the marked text
        document_data["bert_friendly"]["marked_text"] = marked_text
        
        # Create special segment versions with markers
        if "segments" in document_data["bert_friendly"] and isinstance(document_data["bert_friendly"]["segments"], list):
            marked_segments = []
            
            # Process segments in batches for memory management
            batch_size = 8 if self.memory_limit else 16
            for i in range(0, len(document_data["bert_friendly"]["segments"]), batch_size):
                batch_segments = document_data["bert_friendly"]["segments"][i:i+batch_size]
                
                # In memory constrained environments, clear caches periodically
                if TEST_ENV and self.memory_limit and i > 0 and i % 32 == 0:
                    if TORCH_AVAILABLE and hasattr(torch, "cuda") and torch.cuda.is_available():
                        torch.cuda.empty_cache()
                        
                    # Log memory usage
                    import resource
                    mem_usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024  # MB
                    logger.debug(f"Memory usage: {mem_usage:.2f} MB")
                    put_cloudwatch_metric("MemoryUsage", mem_usage, "Megabytes")
                
                for segment in batch_segments:
                    marked_segment = self._mark_argument_components(segment["text"])
                    marked_segments.append({
                        "text": marked_segment,
                        "tokens": segment["tokens"],
                        "paragraphs": segment["paragraphs"]
                    })
            
            document_data["bert_friendly"]["marked_segments"] = marked_segments
            
            # Store to S3 if enabled and large
            if self.use_s3 and "file_id" in document_data.get("metadata", {}) and len(marked_segments) > 10:
                file_id = document_data["metadata"]["file_id"]
                s3_key = f"document_processing/{file_id}/marked_segments.json"
                s3_uri = save_to_s3({"marked_segments": marked_segments}, s3_key)
                
                if s3_uri:
                    # Replace with S3 reference
                    document_data["bert_friendly"]["marked_segments"] = "See S3 reference"
                    document_data["bert_friendly"]["s3_reference_marked_segments"] = s3_uri
        
        return document_data
    
    @timed_execution
    def add_linguistic_features(self, document_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add pre-computed linguistic features.
        
        Args:
            document_data: Document data dictionary
            
        Returns:
            Document data with linguistic features added
        """
        # Get text from document data or S3
        text = document_data["content"].get("full_text", "")
        if not text and self.use_s3 and "s3_references" in document_data:
            if "full_text" in document_data["s3_references"].get("content", {}):
                s3_key = document_data["s3_references"]["content"]["full_text"]
                text_content = load_from_s3(s3_key)
                if text_content is not None:
                    text = text_content
                    document_data["content"]["full_text"] = text
        
        paragraphs = document_data["content"].get("paragraphs", [])
        if not paragraphs and self.use_s3 and "s3_references" in document_data:
            if "paragraphs" in document_data["s3_references"].get("content", {}):
                s3_key = document_data["s3_references"]["content"]["paragraphs"]
                paragraphs_data = load_from_s3(s3_key)
                if paragraphs_data is not None:
                    paragraphs = paragraphs_data
                    document_data["content"]["paragraphs"] = paragraphs
        
        sentences = document_data["content"].get("sentences", [])
        if not sentences and self.use_s3 and "s3_references" in document_data:
            if "sentences" in document_data["s3_references"].get("content", {}):
                s3_key = document_data["s3_references"]["content"]["sentences"]
                sentences_data = load_from_s3(s3_key)
                if sentences_data is not None:
                    sentences = sentences_data
                    document_data["content"]["sentences"] = sentences
                    
        # Skip feature calculation if text is empty
        if not text:
            document_data["features"]["readability"] = {}
            document_data["features"]["complexity"] = {}
            document_data["features"]["paragraph_stats"] = {}
            document_data["features"]["stylistic_features"] = {}
            return document_data
            
        # Calculate readability metrics
        try:
            readability = {
                "flesch_reading_ease": textstat.flesch_reading_ease(text),
                "flesch_kincaid_grade": textstat.flesch_kincaid_grade(text),
                "smog_index": textstat.smog_index(text),
                "automated_readability_index": textstat.automated_readability_index(text),
                "dale_chall_readability_score": textstat.dale_chall_readability_score(text)
            }
        except Exception as e:
            logger.warning(f"Error calculating readability metrics: {e}")
            readability = {}
        
        # Calculate complexity metrics
        try:
            if sentences:
                avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences)
                std_sentence_length = np.std([len(s.split()) for s in sentences])
            else:
                avg_sentence_length = 0
                std_sentence_length = 0
                
            words = text.split()
            avg_word_length = sum(len(word) for word in words) / max(1, len(words))
            
            unique_words = set(word.lower() for word in words)
            unique_word_ratio = len(unique_words) / max(1, len(words))
            
            complexity = {
                "avg_sentence_length": avg_sentence_length,
                "std_sentence_length": std_sentence_length,
                "avg_word_length": avg_word_length,
                "unique_word_ratio": unique_word_ratio,
                "lexical_diversity": self._measure_lexical_diversity(text)
            }
        except Exception as e:
            logger.warning(f"Error calculating complexity metrics: {e}")
            complexity = {}
        
        # Calculate paragraph statistics
        try:
            if paragraphs:
                avg_paragraph_length = sum(len(p.split()) for p in paragraphs) / len(paragraphs)
                std_paragraph_length = np.std([len(p.split()) for p in paragraphs])
            else:
                avg_paragraph_length = 0
                std_paragraph_length = 0
                
            paragraph_stats = {
                "paragraph_count": len(paragraphs),
                "avg_paragraph_length": avg_paragraph_length,
                "std_paragraph_length": std_paragraph_length,
                "max_paragraph_length": max([len(p.split()) for p in paragraphs]) if paragraphs else 0,
                "min_paragraph_length": min([len(p.split()) for p in paragraphs]) if paragraphs else 0
            }
        except Exception as e:
            logger.warning(f"Error calculating paragraph statistics: {e}")
            paragraph_stats = {}
        
        # Calculate stylistic features - use a subset for Lambda optimization
        try:
            stylistic_features = self._calculate_stylistic_features(text, sentences)
        except Exception as e:
            logger.warning(f"Error calculating stylistic features: {e}")
            stylistic_features = {}
        
        # Update document data
        document_data["features"] = {
            "readability": readability,
            "complexity": complexity,
            "paragraph_stats": paragraph_stats,
            "stylistic_features": stylistic_features,
            "document_stats": document_data["features"].get("document_stats", {})
        }
        
        # Add segment-level features if segments exist
        if "segments" in document_data["bert_friendly"] and isinstance(document_data["bert_friendly"]["segments"], list):
            # Only process segments if not test environment with tight memory
            if not (TEST_ENV and self.memory_limit > 0 and len(document_data["bert_friendly"]["segments"]) > 10):
                self._add_segment_features(document_data)
            else:
                logger.info("Skipping segment features due to memory constraints")
        
        return document_data
    
    def add_document_embedding(self, document_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add embedding for the entire document.
        
        Args:
            document_data: Document data dictionary
            
        Returns:
            Document data with document embedding added
        """
        # Skip if PyTorch is not available or in test mode with memory constraints
        if not TORCH_AVAILABLE or (TEST_ENV and self.memory_limit > 0):
            logger.info("Skipping document embedding due to environment constraints")
            return document_data
            
        try:
            # Load model for embedding generation
            model_name = TOKENIZER_CONFIG["test" if TEST_ENV else "production"]["small"]
            
            # Use EFS cache dir if available
            cache_dir = MODEL_CACHE_DIR if MODEL_CACHE_DIR else None
            
            # Load model with appropriate cache settings
            if cache_dir:
                model = AutoModel.from_pretrained(model_name, cache_dir=cache_dir)
            else:
                # For Lambda, use temporary directory
                tmp_cache = '/tmp/transformers_cache'
                os.makedirs(tmp_cache, exist_ok=True)
                model = AutoModel.from_pretrained(model_name, cache_dir=tmp_cache)
            
            # Generate embeddings for segments - limit number for Lambda
            segment_embeddings = []
            if "segments" in document_data["bert_friendly"] and isinstance(document_data["bert_friendly"]["segments"], list):
                # Limit the number of segments to process
                max_segments = 5 if TEST_ENV else 10
                segments_to_process = document_data["bert_friendly"]["segments"][:max_segments]
                
                for segment in segments_to_process:
                    inputs = self.tokenizer(
                        segment["text"],
                        return_tensors="pt",
                        truncation=True,
                        max_length=512
                    )
                    with torch.no_grad():
                        outputs = model(**inputs)
                    
                    # Use the CLS token embedding as segment embedding
                    segment_embedding = outputs.last_hidden_state[:, 0, :].numpy()
                    segment_embeddings.append(segment_embedding.flatten().tolist())
                
                # If we have segment embeddings, compute document embedding as average
                if segment_embeddings:
                    document_embedding = np.mean(segment_embeddings, axis=0).tolist()
                    document_data["bert_friendly"]["document_embedding"] = document_embedding
                    document_data["bert_friendly"]["segment_embeddings"] = segment_embeddings
                    
                    # Store embeddings to S3 if enabled
                    if self.use_s3 and "file_id" in document_data.get("metadata", {}):
                        file_id = document_data["metadata"]["file_id"]
                        s3_key = f"document_processing/{file_id}/embeddings.json"
                        embeddings_data = {
                            "document_embedding": document_embedding,
                            "segment_embeddings": segment_embeddings
                        }
                        s3_uri = save_to_s3(embeddings_data, s3_key)
                        
                        if s3_uri:
                            # Replace with S3 reference if very large
                            if len(str(segment_embeddings)) > 10000:
                                document_data["bert_friendly"]["segment_embeddings"] = "See S3 reference"
                                document_data["bert_friendly"]["s3_reference_embeddings"] = s3_uri
                
            # Clean up
            del model
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                
        except Exception as e:
            logger.warning(f"Error generating document embedding: {e}", exc_info=True)
            # Continue without embeddings
            pass
        
        return document_data
    
    def _create_alternative_segments(self, sentences: List[str], max_length: int) -> List[Dict[str, Any]]:
        """
        Create alternative segments based on sentences.
        
        Args:
            sentences: List of sentences
            max_length: Maximum sequence length for BERT
            
        Returns:
            List of alternative segments
        """
        alternative_segments = []
        current_segment = ""
        current_tokens = 0
        sentence_indices = []
        
        # Skip if empty or not enough sentences
        if not sentences:
            return alternative_segments
            
        # If in test environment with memory constraints, limit processing
        if TEST_ENV and self.memory_limit > 0 and len(sentences) > 50:
            logger.info(f"Limiting alternative segmentation to 50 sentences (from {len(sentences)})")
            sentences = sentences[:50]
            
        for i, sentence in enumerate(sentences):
            # Skip very short sentences
            if len(sentence.split()) < 3:
                continue
                
            # Tokenize sentence
            tokens = len(self.tokenizer.encode(sentence, add_special_tokens=False))
            
            # If adding this sentence would exceed the limit
            if current_tokens + tokens > max_length - 2:  # -2 for [CLS] and [SEP]
                if current_segment:
                    # Add current segment to the list
                    alternative_segments.append({
                        "text": current_segment.strip(),
                        "tokens": current_tokens + 2,  # +2 for [CLS] and [SEP]
                        "sentence_indices": sentence_indices
                    })
                
                # Start a new segment
                current_segment = sentence
                current_tokens = tokens
                sentence_indices = [i]
            else:
                # Add sentence to current segment
                if current_segment:
                    current_segment += " " + sentence
                else:
                    current_segment = sentence
                current_tokens += tokens
                sentence_indices.append(i)
        
        # Add the last segment if it exists
        if current_segment:
            alternative_segments.append({
                "text": current_segment.strip(),
                "tokens": current_tokens + 2,  # +2 for [CLS] and [SEP]
                "sentence_indices": sentence_indices
            })
        
        return alternative_segments
    
    def _mark_argument_components(self, text: str) -> str:
        """
        Add markers for argument components using rule-based patterns.
        
        Args:
            text: Text to mark
            
        Returns:
            Text with argument component markers
        """
        # Skip if text is empty or too long
        if not text or (TEST_ENV and self.memory_limit > 0 and len(text) > 10000):
            return text
            
        # Define markers
        ARGUMENT_START = "[ARG]"
        CLAIM_START = "[CLAIM]"
        EVIDENCE_START = "[EVIDENCE]"
        CONCLUSION_START = "[CONCLUSION]"
        
        # Pattern for claims
        claim_patterns = [
            r"(?i)(I|we) (believe|think|argue|contend) that",
            r"(?i)It is (clear|evident|obvious) that",
            r"(?i)(Our|My) position is",
            r"(?i)(I|we) (support|oppose)",
            r"(?i)The (issue|problem|challenge) is",
            r"(?i)(I|we) would like to (emphasize|highlight)"
        ]
        
        # Pattern for evidence
        evidence_patterns = [
            r"(?i)For (example|instance)",
            r"(?i)Evidence (shows|suggests|indicates)",
            r"(?i)(According to|As stated by)",
            r"(?i)Research (shows|suggests|indicates)",
            r"(?i)Studies (show|suggest|indicate)",
            r"(?i)Data (shows|proves|indicates)",
            r"(?i)Statistics (show|suggest|indicate)"
        ]
        
        # Pattern for conclusions
        conclusion_patterns = [
            r"(?i)In conclusion",
            r"(?i)To (summarize|conclude)",
            r"(?i)In summary",
            r"(?i)Therefore, (I|we) (believe|suggest|recommend)",
            r"(?i)In light of these (facts|considerations|arguments)",
            r"(?i)As a result",
            r"(?i)Consequently"
        ]
        
        marked_text = text
        
        # Mark claims
        for pattern in claim_patterns:
            marked_text = re.sub(
                f"({pattern})",
                f"{CLAIM_START} \\1",
                marked_text
            )
        
        # Mark evidence
        for pattern in evidence_patterns:
            marked_text = re.sub(
                f"({pattern})",
                f"{EVIDENCE_START} \\1",
                marked_text
            )
        
        # Mark conclusions
        for pattern in conclusion_patterns:
            marked_text = re.sub(
                f"({pattern})",
                f"{CONCLUSION_START} \\1",
                marked_text
            )
        
        # Mark argument blocks - sentences that don't have specific markers but are part of an argument
        # Skip this step in memory-constrained environments as it's more processing-intensive
        if not (TEST_ENV and self.memory_limit > 0):
            sentences = nltk.sent_tokenize(marked_text)
            for i, sentence in enumerate(sentences):
                # If sentence doesn't have a marker but is between marked sentences, mark it as part of an argument
                if (i > 0 and i < len(sentences) - 1 and
                    not any(marker in sentence for marker in [CLAIM_START, EVIDENCE_START, CONCLUSION_START]) and
                    any(marker in sentences[i-1] for marker in [CLAIM_START, EVIDENCE_START, CONCLUSION_START]) and
                    any(marker in sentences[i+1] for marker in [CLAIM_START, EVIDENCE_START, CONCLUSION_START])):
                    marked_sentence = f"{ARGUMENT_START} {sentence}"
                    marked_text = marked_text.replace(sentence, marked_sentence)
        
        return marked_text
    
    def _measure_lexical_diversity(self, text: str) -> float:
        """
        Measure lexical diversity (type-token ratio).
        
        Args:
            text: Text to analyze
            
        Returns:
            Lexical diversity score
        """
        # Skip if text is empty
        if not text:
            return 0.0
            
        words = [word.lower() for word in text.split() if word.isalpha()]
        if not words:
            return 0.0
        
        # For very long texts in memory-constrained environments, sample the text
        if TEST_ENV and self.memory_limit > 0 and len(words) > 5000:
            import random
            # Sample 5000 words randomly
            words = random.sample(words, 5000)
        
        unique_words = set(words)
        
        # Use a corrected type-token ratio to account for text length
        if len(words) < 100:
            # Simple type-token ratio for short texts
            diversity = len(unique_words) / len(words)
        else:
            # Moving-average type-token ratio for longer texts
            # This helps mitigate the effect of text length on the measure
            window_size = 100
            diversity_values = []
            
            # In memory constrained environments, use fewer steps
            step_size = 50 if not (TEST_ENV and self.memory_limit > 0) else 100
            
            for i in range(0, len(words) - window_size + 1, step_size):  # 50% overlap normally, no overlap in constrained mode
                window = words[i:i+window_size]
                window_unique = set(window)
                diversity_values.append(len(window_unique) / window_size)
            
            diversity = sum(diversity_values) / len(diversity_values)
        
        return diversity
    
    def _calculate_stylistic_features(self, text: str, sentences: List[str]) -> Dict[str, Any]:
        """
        Calculate stylistic features of the text.
        
        Args:
            text: Full text
            sentences: List of sentences
            
        Returns:
            Dictionary of stylistic features
        """
        # Skip if text is empty
        if not text or not sentences:
            return {}
            
        # For very long texts in memory-constrained environments, limit processing
        if TEST_ENV and self.memory_limit > 0:
            if len(text) > 20000:  # ~5000 words
                # Take first 5000 words for analysis
                words = text.split()[:5000]
                text = ' '.join(words)
                
            if len(sentences) > 200:
                # Take first 200 sentences for analysis
                sentences = sentences[:200]
        
        # Initialize features dictionary
        stylistic_features = {}
        
        try:
            # Calculate frequency of various stylistic markers
            words = text.split()
            total_words = len(words)
            
            if total_words == 0:
                return {}
            
            # First-person pronouns (indicates personal opinion)
            first_person_pattern = r'\b(I|me|my|mine|we|us|our|ours)\b'
            first_person_count = len(re.findall(first_person_pattern, text, re.IGNORECASE))
            stylistic_features["first_person_ratio"] = first_person_count / total_words
            
            # Third-person pronouns (indicates formal, objective style)
            third_person_pattern = r'\b(he|him|his|she|her|hers|it|its|they|them|their|theirs)\b'
            third_person_count = len(re.findall(third_person_pattern, text, re.IGNORECASE))
            stylistic_features["third_person_ratio"] = third_person_count / total_words
            
            # Question frequency (indicates Socratic/questioning style)
            question_count = len([s for s in sentences if s.strip().endswith('?')])
            stylistic_features["question_ratio"] = question_count / max(1, len(sentences))
            
            # In memory-constrained test environments, skip the more expensive analysis
            if TEST_ENV and self.memory_limit > 0:
                return stylistic_features
            
            # Imperative sentences (indicates directive/commanding style)
            imperative_patterns = [
                r'^([A-Z][a-z]+\s+)+\.',  # Capitalized word(s) followed by period
                r'\b(Consider|Note|Remember|Observe|Let|Do|Make|Think|Try)\b'  # Common imperative starters
            ]
            imperative_count = 0
            for pattern in imperative_patterns:
                imperative_count += len(re.findall(pattern, text))
            stylistic_features["imperative_ratio"] = imperative_count / max(1, len(sentences))
            
            # Passive voice (indicates formal, academic style)
            passive_patterns = [
                r'\b(is|are|was|were|be|been|being)\s+([a-z]+ed|[a-z]+en)\b',
                r'\b(has|have|had)\s+been\s+([a-z]+ed|[a-z]+en)\b'
            ]
            passive_count = 0
            for pattern in passive_patterns:
                passive_count += len(re.findall(pattern, text, re.IGNORECASE))
            stylistic_features["passive_ratio"] = passive_count / max(1, len(sentences))
            
            # Hedging (indicates cautious/tentative style)
            hedging_words = [
                'may', 'might', 'could', 'possibly', 'perhaps', 'probably',
                'approximately', 'roughly', 'suggests', 'indicates', 'seems',
                'appears', 'tends', 'somewhat', 'somehow', 'likely', 'unlikely'
            ]
            hedging_count = sum(1 for word in words if word.lower() in hedging_words)
            stylistic_features["hedging_ratio"] = hedging_count / total_words
            
            # Boosting (indicates confident/assertive style)
            boosting_words = [
                'definitely', 'certainly', 'clearly', 'obviously', 'absolutely',
                'undoubtedly', 'without doubt', 'surely', 'indeed', 'of course',
                'always', 'never', 'extremely', 'very', 'particularly', 'especially'
            ]
            boosting_count = sum(1 for word in words if word.lower() in boosting_words)
            stylistic_features["boosting_ratio"] = boosting_count / total_words
            
            # Connectives (indicates argumentative style)
            connectives = [
                'therefore', 'thus', 'consequently', 'as a result', 'hence',
                'so', 'because', 'since', 'due to', 'owing to', 'in contrast',
                'however', 'although', 'despite', 'nevertheless', 'nonetheless',
                'whereas', 'while', 'on the other hand', 'furthermore', 'moreover',
                'in addition', 'additionally', 'besides', 'also', 'similarly',
                'likewise', 'for example', 'for instance', 'specifically', 'in particular'
            ]
            connective_count = sum(1 for i in range(len(words)-1) if ' '.join(words[i:i+2]).lower() in connectives)
            connective_count += sum(1 for word in words if word.lower() in connectives)
            stylistic_features["connective_ratio"] = connective_count / total_words
        
        except Exception as e:
            logger.warning(f"Error calculating stylistic features: {e}")
        
        return stylistic_features
    
    def _add_segment_features(self, document_data: Dict[str, Any]) -> None:
        """
        Add features for each segment.
        
        Args:
            document_data: Document data dictionary
        """
        # Skip if segments aren't available or not a list
        if ("segments" not in document_data["bert_friendly"] or 
            not isinstance(document_data["bert_friendly"]["segments"], list)):
            return
            
        # Get segments
        segments = document_data["bert_friendly"]["segments"]
        
        # For memory constrained environments, limit the number of segments processed
        if TEST_ENV and self.memory_limit > 0 and len(segments) > 10:
            logger.info(f"Limiting segment feature calculation to 10 segments (from {len(segments)})")
            segments_to_process = segments[:10]
        else:
            segments_to_process = segments
            
        # Compute features for each segment
        for i, segment in enumerate(segments_to_process):
            # Skip if we're beyond the segments we want to process
            if i >= len(segments):
                break
                
            segment_text = segment["text"]
            
            try:
                # Tokenize into sentences
                segment_sentences = nltk.sent_tokenize(segment_text)
                
                # Basic statistics
                words = segment_text.split()
                
                # Readability
                flesch_score = textstat.flesch_reading_ease(segment_text)
                
                # Complexity
                avg_sentence_length = sum(len(s.split()) for s in segment_sentences) / max(1, len(segment_sentences))
                unique_words = set(word.lower() for word in words)
                unique_word_ratio = len(unique_words) / max(1, len(words))
                
                # Argument markers
                claim_count = segment_text.count("[CLAIM]")
                evidence_count = segment_text.count("[EVIDENCE]")
                conclusion_count = segment_text.count("[CONCLUSION]")
                
                # Update segment with features
                document_data["bert_friendly"]["segments"][i]["features"] = {
                    "word_count": len(words),
                    "sentence_count": len(segment_sentences),
                    "flesch_score": flesch_score,
                    "avg_sentence_length": avg_sentence_length,
                    "unique_word_ratio": unique_word_ratio,
                    "claim_count": claim_count,
                    "evidence_count": evidence_count,
                    "conclusion_count": conclusion_count
                }
            
            except Exception as e:
                logger.warning(f"Error calculating features for segment {i}: {e}")
                document_data["bert_friendly"]["segments"][i]["features"] = {}


# Lambda handler for AWS Lambda
def lambda_handler(event, context):
    """
    AWS Lambda handler for BERT formatting.
    
    Args:
        event: Lambda event
        context: Lambda context
        
    Returns:
        Formatted document data
    """
    start_time = time.time()
    
    try:
        # Check if input is from S3
        s3_key = event.get('s3_key')
        document_data = None
        
        if s3_key:
            # Load document data from S3
            document_data = load_from_s3(s3_key)
            if not document_data:
                return {
                    'statusCode': 404,
                    'body': json.dumps({
                        'error': f"Document not found in S3: {s3_key}"
                    })
                }
        else:
            # Get document data from event
            document_data = event.get('document_data')
            
        if not document_data:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': "No document data provided"
                })
            }
        
        # Get formatter configuration
        model_name = event.get('model_name', None)
        variant = event.get('variant', 'default')
        memory_limit = int(event.get('memory_limit', 0)) or MEMORY_LIMIT_MB
        use_s3 = event.get('use_s3', USE_S3)
        
        # Initialize formatter
        formatter = BertFormatter.get_instance(
            model_name=model_name,
            variant=variant,
            memory_limit=memory_limit,
            use_s3=use_s3
        )
        
        # Format document for BERT
        result = formatter.format_for_bert(document_data)
        
        # Determine output
        if s3_key:
            # Save result back to S3
            output_key = s3_key.replace('.json', '.bert_formatted.json')
            s3_uri = save_to_s3(result, output_key)
            
            if not s3_uri:
                return {
                    'statusCode': 500,
                    'body': json.dumps({
                        'error': f"Failed to save result to S3: {output_key}"
                    })
                }
            
            # Return S3 reference
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'success': True,
                    's3_uri': s3_uri,
                    'processing_time_ms': (time.time() - start_time) * 1000
                })
            }
        else:
            # Return full result in response
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'success': True,
                    'document_data': result,
                    'processing_time_ms': (time.time() - start_time) * 1000
                })
            }
    
    except Exception as e:
        logger.error(f"Error in lambda_handler: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }


# Testing function if run directly
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Format documents for BERT processing")
    parser.add_argument("--file", help="Path to document JSON file")
    parser.add_argument("--s3", help="S3 key to document JSON file")
    parser.add_argument("--output", help="Output file path (default: input file with .bert.json suffix)")
    parser.add_argument("--model", help="Model name for tokenization", default=None)
    parser.add_argument("--variant", help="Model variant (default, small, multilingual)", default="default")
    parser.add_argument("--test", action="store_true", help="Use test configuration")
    parser.add_argument("--memory-limit", type=int, help="Memory limit in MB (0 for no limit)", default=0)
    parser.add_argument("--use-s3", action="store_true", help="Use S3 for storage")
    parser.add_argument("--no-s3", action="store_true", help="Don't use S3 for storage")
    
    args = parser.parse_args()
    
    if args.test:
        os.environ["TEST_ENV"] = "true"
        print("Using test configuration")
    
    if args.memory_limit > 0:
        os.environ["MEMORY_LIMIT_MB"] = str(args.memory_limit)
        print(f"Setting memory limit to {args.memory_limit} MB")
    
    # Determine S3 usage
    use_s3 = USE_S3
    if args.use_s3:
        use_s3 = True
    elif args.no_s3:
        use_s3 = False
    
    if not args.file and not args.s3:
        print("Please provide either a local file path or an S3 key")
        exit(1)
    
    try:
        # Initialize document data
        document_data = None
        
        if args.s3:
            # Load from S3
            document_data = load_from_s3(args.s3)
            if not document_data:
                print(f"Error loading document from S3: {args.s3}")
                exit(1)
        else:
            # Load from local file
            with open(args.file, 'r', encoding='utf-8') as f:
                document_data = json.load(f)
        
        # Initialize formatter
        formatter = BertFormatter(
            model_name=args.model,
            variant=args.variant,
            memory_limit=args.memory_limit,
            use_s3=use_s3
        )
        
        # Format document
        document_data = formatter.format_for_bert(document_data)
        
        # Save result
        if args.output:
            output_path = args.output
        elif args.file:
            output_path = args.file.replace('.json', '.bert.json')
        else:
            output_path = f"bert_output_{int(time.time())}.json"
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(document_data, f, indent=2, ensure_ascii=False)
        
        print(f"Successfully formatted document and saved to {output_path}")
        
        # Print segments stats if available
        if "bert_friendly" in document_data and "segment_count" in document_data["bert_friendly"]:
            print(f"Created {document_data['bert_friendly']['segment_count']} segments")
            print(f"Total token count: {document_data['bert_friendly'].get('token_count', 0)}")
    
    except Exception as e:
        print(f"Error formatting for BERT: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
