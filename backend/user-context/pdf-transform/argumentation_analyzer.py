#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Argumentation Analyzer Module

This module analyzes argumentative structures in text using transformer-based models.
It identifies argument components (claims, premises, etc.) and their relationships,
as well as patterns of reasoning.

Optimized for AWS Lambda with S3 integration and EFS model caching.
"""

import re
import os
import json
import time
import logging
from typing import Dict, List, Any, Tuple, Optional, Union
from functools import lru_cache

# AWS imports
import boto3
import botocore
from botocore.exceptions import ClientError

# ML imports
import torch
import nltk
from nltk.tokenize import sent_tokenize
from transformers import (
    AutoTokenizer, 
    AutoModelForSequenceClassification, 
    AutoModelForTokenClassification,
    pipeline
)
import numpy as np

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

# Ensure NLTK resources are available
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)

# S3 utility functions
def save_to_s3(data: Union[Dict, List], s3_key: str) -> str:
    """
    Save data to S3.
    
    Args:
        data: Data to save
        s3_key: S3 object key
        
    Returns:
        S3 URI
    """
    if not USE_S3 or s3_client is None:
        return None
    
    try:
        s3_client.put_object(
            Body=json.dumps(data, indent=2),
            Bucket=S3_BUCKET,
            Key=s3_key,
            ContentType='application/json'
        )
        logger.info(f"Saved data to s3://{S3_BUCKET}/{s3_key}")
        return f"s3://{S3_BUCKET}/{s3_key}"
    except ClientError as e:
        logger.error(f"Error saving to S3: {e}", exc_info=True)
        return None

def load_from_s3(s3_key: str) -> Union[Dict, List, None]:
    """
    Load data from S3.
    
    Args:
        s3_key: S3 object key
        
    Returns:
        Loaded data
    """
    if not USE_S3 or s3_client is None:
        return None
    
    try:
        response = s3_client.get_object(Bucket=S3_BUCKET, Key=s3_key)
        data = json.loads(response['Body'].read().decode('utf-8'))
        logger.info(f"Loaded data from s3://{S3_BUCKET}/{s3_key}")
        return data
    except ClientError as e:
        logger.error(f"Error loading from S3: {e}", exc_info=True)
        return None

def put_cloudwatch_metric(name: str, value: float, unit: str = 'Milliseconds', namespace: str = 'ArgumentationAnalyzer'):
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

# Model configuration for different environments
MODEL_CONFIG = {
    "production": {
        "component_model": "mtei/distilroberta-argument-component-detection",
        "relation_model": "mtei/bert-base-argument-relation-classification",
        "reasoning_model": "distilbert-base-uncased-finetuned-mnli"
    },
    "test": {
        "component_model": "distilbert-base-uncased",
        "relation_model": "distilbert-base-uncased",
        "reasoning_model": "distilbert-base-uncased"
    }
}

# Global cache for model pipelines
_cached_pipelines = {}

# Timing decorator for performance metrics
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

class ArgumentationAnalyzer:
    """Class for analyzing argumentation structures in text"""
    
    # Class-level shared instance
    _instance = None
    
    @classmethod
    def get_instance(cls, **kwargs):
        """Get a singleton instance of the analyzer"""
        if cls._instance is None:
            cls._instance = cls(**kwargs)
        return cls._instance
    
    def __init__(
        self, 
        component_model: str = None,
        relation_model: str = None,
        reasoning_model: str = None,
        use_gpu: bool = False,
        model_cache_dir: str = MODEL_CACHE_DIR
    ):
        """
        Initialize the argumentation analyzer.
        
        Args:
            component_model: Model for argument component detection
            relation_model: Model for argument relation classification
            reasoning_model: Model for reasoning pattern classification
            use_gpu: Whether to use GPU for inference
            model_cache_dir: Directory to cache models (e.g., EFS mount)
        """
        # Use environment-specific models
        env = "test" if TEST_ENV else "production"
        self.device = "cuda" if use_gpu and torch.cuda.is_available() else "cpu"
        
        # Set model names from config or parameters
        self.component_model_name = component_model or MODEL_CONFIG[env]["component_model"]
        self.relation_model_name = relation_model or MODEL_CONFIG[env]["relation_model"]
        self.reasoning_model_name = reasoning_model or MODEL_CONFIG[env]["reasoning_model"]
        
        # Set model cache directory for EFS
        if model_cache_dir and os.path.exists(model_cache_dir):
            os.environ['TRANSFORMERS_CACHE'] = model_cache_dir
            logger.info(f"Using model cache directory: {model_cache_dir}")
        
        logger.info(f"Using device: {self.device}")
        logger.info(f"Environment: {env}")
        
        # Initialize when first needed (lazy initialization)
        self.component_pipeline = None
        self.relation_pipeline = None
        self.reasoning_pipeline = None
        self.component_tokenizer = None
        self.relation_tokenizer = None
        
        # Flag to track initialization
        self._initialized = False
    
    def initialize_models(self):
        """Initialize models and pipelines (can be called separately from constructor)"""
        if self._initialized:
            logger.debug("Models already initialized")
            return
        
        # Set up global cache key based on model names and device
        cache_key = f"{self.component_model_name}_{self.relation_model_name}_{self.reasoning_model_name}_{self.device}"
        
        # Check if models are already cached
        global _cached_pipelines
        if cache_key in _cached_pipelines:
            logger.info("Using cached model pipelines")
            cached = _cached_pipelines[cache_key]
            self.component_pipeline = cached["component"]
            self.relation_pipeline = cached["relation"]
            self.reasoning_pipeline = cached["reasoning"]
            self.component_tokenizer = cached["component_tokenizer"]
            self.relation_tokenizer = cached["relation_tokenizer"]
            self._initialized = True
            return
            
        logger.info("Initializing model pipelines")
        
        # Set lower precision for Lambda
        torch_dtype = torch.float16 if self.device == "cuda" else torch.float32
        
        try:
            # Start Component Pipeline initialization
            start_time = time.time()
            
            # Initialize argument component detection pipeline
            self.component_pipeline = pipeline(
                "text-classification",
                model=self.component_model_name,
                device=self.device if self.device == "cuda" else -1,
                torch_dtype=torch_dtype
            )
            component_time = time.time() - start_time
            logger.info(f"Loaded argument component model in {component_time:.2f}s")
            put_cloudwatch_metric("ComponentModelLoadTime", component_time * 1000)
            
            # Initialize relation classification pipeline
            start_time = time.time()
            self.relation_pipeline = pipeline(
                "text-classification",
                model=self.relation_model_name,
                device=self.device if self.device == "cuda" else -1,
                torch_dtype=torch_dtype
            )
            relation_time = time.time() - start_time
            logger.info(f"Loaded relation model in {relation_time:.2f}s")
            put_cloudwatch_metric("RelationModelLoadTime", relation_time * 1000)
            
            # Initialize reasoning pattern classification pipeline
            start_time = time.time()
            self.reasoning_pipeline = pipeline(
                "text-classification",
                model=self.reasoning_model_name,
                device=self.device if self.device == "cuda" else -1,
                torch_dtype=torch_dtype
            )
            reasoning_time = time.time() - start_time
            logger.info(f"Loaded reasoning model in {reasoning_time:.2f}s")
            put_cloudwatch_metric("ReasoningModelLoadTime", reasoning_time * 1000)
            
            # Get tokenizers for token count estimation
            self.component_tokenizer = AutoTokenizer.from_pretrained(self.component_model_name)
            self.relation_tokenizer = AutoTokenizer.from_pretrained(self.relation_model_name)
            
            # Cache the pipelines for reuse
            _cached_pipelines[cache_key] = {
                "component": self.component_pipeline,
                "relation": self.relation_pipeline,
                "reasoning": self.reasoning_pipeline,
                "component_tokenizer": self.component_tokenizer,
                "relation_tokenizer": self.relation_tokenizer
            }
            
            self._initialized = True
            
        except Exception as e:
            logger.error(f"Error initializing argumentation analyzer: {e}", exc_info=True)
            # In test environment, create mock pipelines
            if TEST_ENV:
                logger.info("Creating mock pipelines for test environment")
                self._create_mock_pipelines()
            else:
                raise
    
    def _create_mock_pipelines(self):
        """Create mock pipelines for testing"""
        def mock_component_pipeline(texts):
            """Mock component classification pipeline"""
            results = []
            for text in texts:
                # Simple logic to assign component types
                if "because" in text.lower() or "since" in text.lower():
                    label = "Premise"
                    score = 0.8
                elif "should" in text.lower() or "must" in text.lower():
                    label = "Claim"
                    score = 0.9
                elif "believe" in text.lower() or "position" in text.lower():
                    label = "MajorClaim" 
                    score = 0.85
                else:
                    label = "NonArgument"
                    score = 0.7
                
                results.append({"label": label, "score": score})
            return results
        
        def mock_relation_pipeline(text_pairs):
            """Mock relation classification pipeline"""
            results = []
            for _ in text_pairs:
                # Alternate between Support and Attack randomly
                import random
                if random.random() > 0.3:
                    label = "Support"
                    score = 0.75
                else:
                    label = "Attack"
                    score = 0.65
                results.append({"label": label, "score": score})
            return results
        
        def mock_reasoning_pipeline(texts, hypothesis=None):
            """Mock reasoning classification pipeline"""
            results = []
            for _ in range(len(texts) if isinstance(texts, list) else 1):
                import random
                r = random.random()
                if r < 0.4:
                    label = "entailment"
                    score = 0.8
                elif r < 0.7:
                    label = "neutral"
                    score = 0.7
                else:
                    label = "contradiction"
                    score = 0.6
                results.append({"label": label, "score": score})
            return results
        
        # Assign mock pipelines
        self.component_pipeline = mock_component_pipeline
        self.relation_pipeline = mock_relation_pipeline
        self.reasoning_pipeline = mock_reasoning_pipeline
        
        # Create dummy tokenizers
        class MockTokenizer:
            def __call__(self, text, *args, **kwargs):
                return {"input_ids": [1] * min(100, len(text.split()))}
        
        self.component_tokenizer = MockTokenizer()
        self.relation_tokenizer = MockTokenizer()
        self._initialized = True
    
    @timed_execution
    def analyze_argumentation(self, document_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze argumentation in document.
        
        Args:
            document_data: Document data dictionary
            
        Returns:
            Document data with argumentation analysis added
        """
        # Initialize models if not already done
        if not self._initialized:
            self.initialize_models()
        
        # Record memory usage for monitoring
        if torch.cuda.is_available():
            mem_allocated = torch.cuda.memory_allocated() / (1024 ** 2)  # MB
            mem_reserved = torch.cuda.memory_reserved() / (1024 ** 2)    # MB
            put_cloudwatch_metric("GpuMemoryAllocated", mem_allocated, "Megabytes")
            put_cloudwatch_metric("GpuMemoryReserved", mem_reserved, "Megabytes")
        
        # Get sentences from the document
        sentences = document_data["content"]["sentences"]
        
        # Get paragraphs for context
        paragraphs = document_data["content"]["paragraphs"]
        
        # Analyze argument components
        start_time = time.time()
        argument_components = self._detect_argument_components(sentences)
        component_time = time.time() - start_time
        put_cloudwatch_metric("ComponentDetectionTime", component_time * 1000)
        
        # Map components to paragraphs
        argument_components = self._map_components_to_paragraphs(argument_components, paragraphs, sentences)
        
        # Analyze relations between components
        start_time = time.time()
        argument_relations = self._analyze_argument_relations(argument_components)
        relation_time = time.time() - start_time
        put_cloudwatch_metric("RelationAnalysisTime", relation_time * 1000)
        
        # Analyze reasoning patterns
        start_time = time.time()
        reasoning_patterns = self._analyze_reasoning_patterns(argument_components)
        reasoning_time = time.time() - start_time
        put_cloudwatch_metric("ReasoningAnalysisTime", reasoning_time * 1000)
        
        # Generate argumentation graph
        argumentation_graph = self._generate_argumentation_graph(argument_components, argument_relations)
        
        # Calculate argumentation metrics
        argumentation_metrics = self._calculate_argumentation_metrics(
            argument_components, argument_relations, reasoning_patterns
        )
        
        # Store results
        document_data["argumentation"] = {
            "components": argument_components,
            "relations": argument_relations,
            "reasoning_patterns": reasoning_patterns,
            "graph": argumentation_graph,
            "metrics": argumentation_metrics
        }
        
        # Save analysis to S3 if enabled
        if USE_S3 and "file_id" in document_data["metadata"]:
            file_id = document_data["metadata"]["file_id"]
            s3_key = f"argumentation/{file_id}/analysis.json"
            save_to_s3(document_data["argumentation"], s3_key)
        
        return document_data
    
    @timed_execution
    def _detect_argument_components(self, sentences: List[str]) -> List[Dict[str, Any]]:
        """
        Detect argument components in sentences.
        
        Args:
            sentences: List of sentences
            
        Returns:
            List of detected argument components
        """
        if not sentences:
            return []
        
        logger.info(f"Detecting argument components in {len(sentences)} sentences")
        
        # Define component labels
        component_labels = {
            "Claim": "A statement that the author believes and wants the reader to accept",
            "Premise": "A statement that provides support or evidence for a claim",
            "MajorClaim": "The main claim of the text, representing the author's stance on the topic",
            "NonArgument": "Text that doesn't serve an argumentative function"
        }
        
        # Process sentences in smaller batches for Lambda
        batch_size = 8 if TEST_ENV else 16
        all_components = []
        
        try:
            for i in range(0, len(sentences), batch_size):
                # Memory optimization - clear CUDA cache between batches if using GPU
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                
                batch = sentences[i:i+batch_size]
                
                # Skip very short sentences to reduce processing time
                valid_indices = [j for j, s in enumerate(batch) if len(s.split()) >= 3]
                valid_sentences = [batch[j] for j in valid_indices]
                
                if not valid_sentences:
                    continue
                
                batch_start = time.time()
                
                try:
                    # Classify sentences as argument components
                    results = self.component_pipeline(valid_sentences)
                    
                    # Record batch processing time
                    batch_time = time.time() - batch_start
                    logger.debug(f"Processed batch of {len(valid_sentences)} sentences in {batch_time:.2f}s")
                    
                    # Process results
                    if isinstance(results, list) and isinstance(results[0], dict):
                        for idx, result in enumerate(results):
                            original_idx = i + valid_indices[idx]
                            sentence = valid_sentences[idx]
                            
                            # Extract label and score
                            label = result["label"]
                            score = result["score"]
                            
                            # Only keep components with score above threshold (higher for smaller test models)
                            threshold = 0.5 if TEST_ENV else 0.6
                            if score >= threshold:
                                component = {
                                    "sentence_idx": original_idx,
                                    "text": sentence,
                                    "component_type": label,
                                    "confidence": score,
                                    "description": component_labels.get(label, ""),
                                    "paragraph_idx": None  # Will be filled in later
                                }
                                all_components.append(component)
                
                except Exception as e:
                    logger.error(f"Error detecting argument components in batch: {e}", exc_info=True)
                    
                    # Report error metric
                    put_cloudwatch_metric("ComponentDetectionErrors", 1, "Count")
        
        except Exception as e:
            logger.error(f"Error in argument component detection: {e}", exc_info=True)
            
            # Return empty list in test environment, raise in production
            if TEST_ENV:
                return []
            raise
        
        # Record component types distribution
        component_counts = {}
        for comp in all_components:
            comp_type = comp["component_type"]
            component_counts[comp_type] = component_counts.get(comp_type, 0) + 1
        
        for comp_type, count in component_counts.items():
            put_cloudwatch_metric(f"Components_{comp_type}", count, "Count")
        
        logger.info(f"Detected {len(all_components)} argument components")
        return all_components
    
    def _map_components_to_paragraphs(
        self, 
        components: List[Dict[str, Any]], 
        paragraphs: List[str], 
        sentences: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Map argument components to their containing paragraphs.
        
        Args:
            components: List of argument components
            paragraphs: List of paragraphs
            sentences: List of sentences
            
        Returns:
            Components with paragraph indices added
        """
        if not components or not paragraphs:
            return components
        
        # Create a mapping from sentence to paragraph
        sentence_to_paragraph = {}
        
        for para_idx, para in enumerate(paragraphs):
            # Get sentences in this paragraph
            para_sentences = sent_tokenize(para)
            
            for sent in para_sentences:
                # Find this sentence in the full list of sentences
                for sent_idx, full_sent in enumerate(sentences):
                    if sent == full_sent or sent in full_sent or full_sent in sent:
                        sentence_to_paragraph[sent_idx] = para_idx
                        break
        
        # Map components to paragraphs
        for i, component in enumerate(components):
            sent_idx = component["sentence_idx"]
            if sent_idx in sentence_to_paragraph:
                components[i]["paragraph_idx"] = sentence_to_paragraph[sent_idx]
            else:
                # If we can't find the paragraph, use heuristics
                text = component["text"]
                for para_idx, para in enumerate(paragraphs):
                    if text in para:
                        components[i]["paragraph_idx"] = para_idx
                        break
        
        return components
    
    @timed_execution
    def _analyze_argument_relations(self, components: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Analyze relations between argument components.
        
        Args:
            components: List of argument components
            
        Returns:
            List of argument relations
        """
        if len(components) < 2:
            return []
        
        logger.info(f"Analyzing relations between {len(components)} components")
        
        relations = []
        
        # Define relation types
        relation_types = {
            "Support": "The source component provides support or evidence for the target component",
            "Attack": "The source component contradicts or undermines the target component",
            "None": "No significant relation exists between the components"
        }
        
        # Check relations between components
        # Limit the number of combinations in Lambda
        max_relations = 50 if TEST_ENV else 100
        relation_count = 0
        
        try:
            # First analyze relations between claims and premises
            for i, source in enumerate(components):
                source_type = source["component_type"]
                
                # Skip non-argumentative text
                if source_type == "NonArgument":
                    continue
                
                for j, target in enumerate(components):
                    # Skip self-relations
                    if i == j:
                        continue
                    
                    target_type = target["component_type"]
                    
                    # Skip non-argumentative text
                    if target_type == "NonArgument":
                        continue
                    
                    # Only check certain relations based on component types
                    valid_relation = False
                    
                    # Premises support claims or major claims
                    if source_type == "Premise" and (target_type == "Claim" or target_type == "MajorClaim"):
                        valid_relation = True
                    
                    # Claims can support major claims or attack other claims
                    elif source_type == "Claim" and target_type == "MajorClaim":
                        valid_relation = True
                    elif source_type == "Claim" and target_type == "Claim" and i != j:
                        valid_relation = True
                    
                    # Check consecutive components or components in the same paragraph
                    in_same_paragraph = (
                        source["paragraph_idx"] is not None and 
                        target["paragraph_idx"] is not None and
                        source["paragraph_idx"] == target["paragraph_idx"]
                    )
                    
                    consecutive = abs(source["sentence_idx"] - target["sentence_idx"]) <= 3
                    
                    if valid_relation and (in_same_paragraph or consecutive):
                        # Limit total relations analyzed to avoid timeouts
                        if relation_count >= max_relations:
                            logger.warning(f"Reached maximum relation count ({max_relations}), stopping analysis")
                            break
                        
                        relation_count += 1
                        
                        try:
                            # Classify relation between components
                            text_pair = [source["text"], target["text"]]
                            result = self.relation_pipeline(text_pair)[0]
                            
                            relation_type = result["label"]
                            confidence = result["score"]
                            
                            # Adjust threshold for test environment
                            threshold = 0.5 if TEST_ENV else 0.6
                            
                            # Only keep significant relations
                            if confidence >= threshold and relation_type != "None":
                                relation = {
                                    "source_idx": i,
                                    "target_idx": j,
                                    "source_type": source_type,
                                    "target_type": target_type,
                                    "relation_type": relation_type,
                                    "confidence": confidence,
                                    "description": relation_types.get(relation_type, "")
                                }
                                relations.append(relation)
                        
                        except Exception as e:
                            logger.error(f"Error analyzing relation: {e}", exc_info=True)
                            put_cloudwatch_metric("RelationAnalysisErrors", 1, "Count")
                
                if relation_count >= max_relations:
                    break
        
        except Exception as e:
            logger.error(f"Error in relation analysis: {e}", exc_info=True)
            
            # Return partial results in test environment
            if TEST_ENV:
                return relations
            raise
        
        # Record relation metrics
        relation_counts = {}
        for rel in relations:
            rel_type = rel["relation_type"]
            relation_counts[rel_type] = relation_counts.get(rel_type, 0) + 1
        
        for rel_type, count in relation_counts.items():
            put_cloudwatch_metric(f"Relations_{rel_type}", count, "Count")
        
        logger.info(f"Detected {len(relations)} argument relations")
        return relations
    
    @timed_execution
    def _analyze_reasoning_patterns(self, components: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Analyze reasoning patterns in argument components.
        
        Args:
            components: List of argument components
            
        Returns:
            List of reasoning patterns
        """
        if not components:
            return []
        
        logger.info("Analyzing reasoning patterns")
        
        reasoning_patterns = []
        
        # Process premise components for reasoning patterns
        premises = [comp for comp in components if comp["component_type"] == "Premise"]
        
        # Limit the number of premises analyzed for Lambda
        max_premises = 10 if TEST_ENV else 20
        premises = premises[:max_premises]
        
        try:
            for idx, premise in enumerate(premises):
                text = premise["text"]
                
                # Skip very short premises
                if len(text.split()) < 5:
                    continue
                
                try:
                    # Classify reasoning pattern
                    # For MNLI model, we'll use entailment patterns to estimate reasoning type
                    hypothesis_patterns = {
                        "deductive": "This is a deductive argument that follows logically from general principles.",
                        "inductive": "This is an inductive argument based on specific examples or patterns.",
                        "abductive": "This is an abductive argument that offers the best explanation for observed facts.",
                        "analogical": "This is an analogical argument that draws parallels between similar situations."
                    }
                    
                    results = []
                    
                    # In test mode, only check first two reasoning types for speed
                    patterns_to_check = list(hypothesis_patterns.items())
                    if TEST_ENV:
                        patterns_to_check = patterns_to_check[:2]
                    
                    for pattern_type, hypothesis in patterns_to_check:
                        try:
                            # Check entailment with each reasoning pattern
                            result = self.reasoning_pipeline(text, hypothesis)[0]
                            results.append((pattern_type, result["label"], result["score"]))
                        except Exception as e:
                            logger.warning(f"Error classifying reasoning pattern '{pattern_type}': {e}")
                    
                    # Get the highest scoring pattern with "entailment" or "neutral" label
                    valid_results = [(pattern, score) for pattern, label, score in results 
                                    if label in ["entailment", "neutral"]]
                    
                    if valid_results:
                        best_pattern, best_score = max(valid_results, key=lambda x: x[1])
                        
                        # Adjust threshold for test environment
                        threshold = 0.5 if TEST_ENV else 0.6
                        
                        # Only keep patterns with sufficient confidence
                        if best_score >= threshold:
                            original_idx = components.index(premise)
                            pattern = {
                                "component_idx": original_idx,
                                "text": text,
                                "reasoning_type": best_pattern,
                                "confidence": best_score,
                                "description": self._get_reasoning_description(best_pattern)
                            }
                            reasoning_patterns.append(pattern)
                
                except Exception as e:
                    logger.error(f"Error analyzing reasoning pattern: {e}", exc_info=True)
                    put_cloudwatch_metric("ReasoningAnalysisErrors", 1, "Count")
        
        except Exception as e:
            logger.error(f"Error in reasoning pattern analysis: {e}", exc_info=True)
            
            # Return partial results in test environment
            if TEST_ENV:
                return reasoning_patterns
            raise
        
        # Record reasoning pattern metrics
        reasoning_counts = {}
        for pattern in reasoning_patterns:
            pattern_type = pattern["reasoning_type"]
            reasoning_counts[pattern_type] = reasoning_counts.get(pattern_type, 0) + 1
        
        for pattern_type, count in reasoning_counts.items():
            put_cloudwatch_metric(f"ReasoningPattern_{pattern_type}", count, "Count")
        
        logger.info(f"Detected {len(reasoning_patterns)} reasoning patterns")
        return reasoning_patterns
    
    def _generate_argumentation_graph(
        self, 
        components: List[Dict[str, Any]], 
        relations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate a graph representation of the argumentation structure.
        
        Args:
            components: List of argument components
            relations: List of argument relations
            
        Returns:
            Dictionary representation of argumentation graph
        """
        if not components:
            return {"nodes": [], "edges": []}
        
        # Create nodes from components
        nodes = []
        for i, component in enumerate(components):
            node = {
                "id": i,
                "type": component["component_type"],
                "text": component["text"],
                "confidence": component["confidence"]
            }
            nodes.append(node)
        
        # Create edges from relations
        edges = []
        for relation in relations:
            edge = {
                "source": relation["source_idx"],
                "target": relation["target_idx"],
                "type": relation["relation_type"],
                "confidence": relation["confidence"]
            }
            edges.append(edge)
        
        # Calculate node centrality (based on number of connections)
        for i, node in enumerate(nodes):
            in_edges = sum(1 for edge in edges if edge["target"] == i)
            out_edges = sum(1 for edge in edges if edge["source"] == i)
            nodes[i]["centrality"] = in_edges + out_edges
        
        return {
            "nodes": nodes,
            "edges": edges
        }
    
    def _calculate_argumentation_metrics(
        self, 
        components: List[Dict[str, Any]], 
        relations: List[Dict[str, Any]], 
        reasoning_patterns: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate metrics about the argumentation structure.
        
        Args:
            components: List of argument components
            relations: List of argument relations
            reasoning_patterns: List of reasoning patterns
            
        Returns:
            Dictionary of argumentation metrics
        """
        # Initialize metrics
        metrics = {}
        
        # Skip if no components
        if not components:
            return {
                "component_counts": {},
                "relation_counts": {},
                "reasoning_counts": {},
                "argument_density": 0,
                "premise_to_claim_ratio": 0,
                "average_premises_per_claim": 0,
                "support_to_attack_ratio": 0,
                "major_claim_presence": False,
                "reasoning_diversity": 0
            }
        
        # Count components by type
        component_counts = {}
        for component in components:
            comp_type = component["component_type"]
            component_counts[comp_type] = component_counts.get(comp_type, 0) + 1
        
        total_components = len(components)
        
        # Count relations by type
        relation_counts = {}
        for relation in relations:
            rel_type = relation["relation_type"]
            relation_counts[rel_type] = relation_counts.get(rel_type, 0) + 1
        
        # Count reasoning patterns by type
        reasoning_counts = {}
        for pattern in reasoning_patterns:
            reason_type = pattern["reasoning_type"]
            reasoning_counts[reason_type] = reasoning_counts.get(reason_type, 0) + 1
        
        # Calculate component percentages
        component_percentages = {
            k: (v / total_components * 100) if total_components > 0 else 0 
            for k, v in component_counts.items()
        }
        
        # Calculate argumentation density
        num_sentences = max([comp["sentence_idx"] for comp in components] + [0]) + 1
        argument_density = total_components / max(1, num_sentences)
        
        # Calculate premise to claim ratio
        claims_count = component_counts.get("Claim", 0) + component_counts.get("MajorClaim", 0)
        premises_count = component_counts.get("Premise", 0)
        premise_to_claim_ratio = premises_count / max(1, claims_count)
        
        # Calculate average premises per claim
        average_premises_per_claim = 0
        claims = [i for i, comp in enumerate(components) 
                 if comp["component_type"] in ["Claim", "MajorClaim"]]
        
        if claims:
            premises_per_claim = []
            for claim_idx in claims:
                # Count premises supporting this claim
                supporting_premises = sum(1 for rel in relations 
                                        if rel["target_idx"] == claim_idx and 
                                        rel["relation_type"] == "Support" and
                                        components[rel["source_idx"]]["component_type"] == "Premise")
                premises_per_claim.append(supporting_premises)
            
            if premises_per_claim:
                average_premises_per_claim = sum(premises_per_claim) / len(premises_per_claim)
        
        # Calculate support to attack ratio
        support_count = relation_counts.get("Support", 0)
        attack_count = relation_counts.get("Attack", 0)
        support_to_attack_ratio = support_count / max(1, attack_count)
        
        # Check for major claim presence
        major_claim_presence = component_counts.get("MajorClaim", 0) > 0
        
        # Calculate reasoning diversity
        reasoning_diversity = len(reasoning_counts) / 4  # 4 is the maximum number of reasoning types
        
        # Store all metrics
        metrics = {
            "component_counts": component_counts,
            "component_percentages": component_percentages,
            "relation_counts": relation_counts,
            "reasoning_counts": reasoning_counts,
            "argument_density": argument_density,
            "premise_to_claim_ratio": premise_to_claim_ratio,
            "average_premises_per_claim": average_premises_per_claim,
            "support_to_attack_ratio": support_to_attack_ratio,
            "major_claim_presence": major_claim_presence,
            "reasoning_diversity": reasoning_diversity
        }
        
        return metrics
    
    def _get_reasoning_description(self, reasoning_type: str) -> str:
        """
        Get description for a reasoning type.
        
        Args:
            reasoning_type: Type of reasoning
            
        Returns:
            Description of the reasoning type
        """
        descriptions = {
            "deductive": (
                "Deductive reasoning starts with general principles and derives specific conclusions. "
                "It follows a logical, step-by-step approach where the conclusion must be true if the premises are true."
            ),
            "inductive": (
                "Inductive reasoning starts with specific observations and identifies patterns to form general conclusions. "
                "It's probabilistic rather than certain, based on observed evidence and examples."
            ),
            "abductive": (
                "Abductive reasoning finds the simplest and most likely explanation for observations. "
                "It's often used in diagnosis, starting with an observation and seeking the most plausible cause."
            ),
            "analogical": (
                "Analogical reasoning compares similar situations to draw conclusions. "
                "It argues that what's true in one situation is likely true in a similar situation."
            )
        }
        
        return descriptions.get(reasoning_type, "Unknown reasoning type")

# Lambda initialization - preload models when container starts
if os.environ.get("AWS_LAMBDA_INITIALIZATION_TYPE") == "provisioned-concurrency":
    try:
        logger.info("Lambda container initializing - preloading models")
        analyzer = ArgumentationAnalyzer.get_instance()
        analyzer.initialize_models()
        logger.info("Preloaded models successfully")
    except Exception as e:
        logger.error(f"Failed to preload models: {e}", exc_info=True)

# Lambda handler for individual processing
def lambda_handler(event, context):
    """
    AWS Lambda handler for argumentation analysis.
    
    Args:
        event: Lambda event
        context: Lambda context
        
    Returns:
        Analysis results
    """
    start_time = time.time()
    logger.info(f"Received event: {json.dumps(event)}")
    
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
        
        # Get analyzer instance
        analyzer = ArgumentationAnalyzer.get_instance()
        
        # Process document
        result = analyzer.analyze_argumentation(document_data)
        
        # Determine output
        if s3_key:
            # Save result back to S3
            output_key = s3_key.replace('/document.json', '/argumentation.json')
            s3_uri = save_to_s3(result["argumentation"], output_key)
            
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
    
    parser = argparse.ArgumentParser(description="Analyze argumentation in documents")
    parser.add_argument("--file", help="Path to document JSON file")
    parser.add_argument("--s3", help="S3 key to document JSON file")
    parser.add_argument("--test", action="store_true", help="Use test configuration")
    parser.add_argument("--output", help="Output file path (default: input file with .arg.json suffix)")
    
    args = parser.parse_args()
    
    if args.test:
        os.environ["TEST_ENV"] = "true"
        print("Using test configuration")
    
    if not args.file and not args.s3:
        print("Please provide either a local file path or an S3 key")
        exit(1)
    
    try:
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
        
        # Initialize analyzer
        analyzer = ArgumentationAnalyzer()
        document_data = analyzer.analyze_argumentation(document_data)
        
        # Save result
        if args.output:
            output_path = args.output
        elif args.file:
            output_path = args.file.replace('.json', '.arg.json')
        else:
            output_path = f"output_{int(time.time())}.json"
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(document_data, f, indent=2, ensure_ascii=False)
        
        print(f"Successfully analyzed argumentation and saved to {output_path}")
        
        # Print metrics
        if "argumentation" in document_data and "metrics" in document_data["argumentation"]:
            metrics = document_data["argumentation"]["metrics"]
            print("\nArgumentation Metrics:")
            for key, value in metrics.items():
                if isinstance(value, dict):
                    print(f"  {key}:")
                    for subkey, subvalue in value.items():
                        if isinstance(subvalue, float):
                            print(f"    {subkey}: {subvalue:.2f}")
                        else:
                            print(f"    {subkey}: {subvalue}")
                elif isinstance(value, float):
                    print(f"  {key}: {value:.2f}")
                else:
                    print(f"  {key}: {value}")
    
    except Exception as e:
        print(f"Error analyzing argumentation: {e}")
        exit(1)
