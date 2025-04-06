#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Metadata Extractor Module

This module extracts metadata from processed documents, including committee,
country, topic, and date information using pattern recognition and NLP techniques.
Optimized for AWS Lambda environments with proper caching and resource management.
"""

import re
import logging
import datetime
import os
import json
import time
import hashlib
import tempfile
from pathlib import Path
from functools import lru_cache
from typing import Dict, List, Optional, Any, Tuple, Union

# Conditionally import AWS modules
AWS_AVAILABLE = False
try:
    import boto3
    from botocore.exceptions import ClientError
    AWS_AVAILABLE = True
except ImportError:
    pass

# Configure environment variables
ENV_TEST_MODE = os.environ.get("TEST_ENV", "false").lower() == "true"
ENV_AWS_LAMBDA = os.environ.get("AWS_LAMBDA_FUNCTION_NAME") is not None
ENV_MEMORY_LIMIT = int(os.environ.get("METADATA_EXTRACTOR_MEMORY_LIMIT", "0"))
ENV_MODEL_CACHE_DIR = os.environ.get("MODEL_CACHE_DIR", "/tmp/model_cache" if ENV_AWS_LAMBDA else "./model_cache")
ENV_USE_SPACY = os.environ.get("USE_SPACY", "true").lower() == "true" and not ENV_TEST_MODE
ENV_USE_TRANSFORMERS = os.environ.get("USE_TRANSFORMERS", "true").lower() == "true" and not ENV_TEST_MODE
ENV_CLOUDWATCH_NAMESPACE = os.environ.get("CLOUDWATCH_METRICS_NAMESPACE", "PDFTransform")
ENV_S3_BUCKET = os.environ.get("PDF_TRANSFORM_S3_BUCKET")
ENV_EFS_MOUNTED = os.path.exists("/mnt/efs") and os.access("/mnt/efs", os.W_OK)

# Configure logging
log_level = logging.INFO if not ENV_AWS_LAMBDA else logging.WARNING
logging.basicConfig(
    level=log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Setup metrics if in AWS environment
metrics = None
if AWS_AVAILABLE and ENV_AWS_LAMBDA:
    try:
        # Initialize CloudWatch client outside of handler for better cold start performance
        cloudwatch = boto3.client('cloudwatch')
        def put_metric(name, value, unit='Count', dimensions=None):
            try:
                if dimensions is None:
                    dimensions = []
                cloudwatch.put_metric_data(
                    Namespace=ENV_CLOUDWATCH_NAMESPACE,
                    MetricData=[{
                        'MetricName': name,
                        'Value': value,
                        'Unit': unit,
                        'Dimensions': dimensions
                    }]
                )
            except Exception as e:
                logger.warning(f"Failed to put CloudWatch metric {name}: {e}")
        
        metrics = {
            'put_metric': put_metric
        }
    except Exception as e:
        logger.warning(f"Failed to initialize CloudWatch metrics: {e}")

# Create cache directory if it doesn't exist
if ENV_EFS_MOUNTED:
    # Use EFS mount for persistent cache if available
    ENV_MODEL_CACHE_DIR = "/mnt/efs/model_cache"
    
model_cache_dir = Path(ENV_MODEL_CACHE_DIR)
if not model_cache_dir.exists():
    try:
        model_cache_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created model cache directory: {model_cache_dir}")
    except Exception as e:
        logger.warning(f"Failed to create model cache directory: {e}")
        ENV_MODEL_CACHE_DIR = tempfile.gettempdir()
        model_cache_dir = Path(ENV_MODEL_CACHE_DIR)

# Configure NLP libraries with appropriate paths
os.environ["TRANSFORMERS_CACHE"] = str(model_cache_dir / "transformers")
os.environ["NLTK_DATA"] = str(model_cache_dir / "nltk_data")

# Import NLP libraries after configuring cache paths
import nltk
nltk_data_path = Path(os.environ["NLTK_DATA"])
if not nltk_data_path.exists():
    nltk_data_path.mkdir(parents=True, exist_ok=True)

# Conditionally import SpaCy and Transformers to reduce cold start time
# if they're not needed
nlp = None
ner_pipeline = None
if ENV_USE_SPACY:
    try:
        import spacy
        # Only load spacy outside the class if we're in Lambda to keep warm
        if ENV_AWS_LAMBDA:
            nlp = spacy.load("en_core_web_sm")
            logger.info("Preloaded SpaCy model for Lambda environment")
    except ImportError:
        logger.warning("SpaCy not available")
        ENV_USE_SPACY = False

if ENV_USE_TRANSFORMERS:
    try:
        from transformers import pipeline
        from sklearn.feature_extraction.text import TfidfVectorizer
        
        # Only load transformers outside the class if we're in Lambda to keep warm
        if ENV_AWS_LAMBDA:
            # Use smaller model in Lambda environment
            model_name = "dslim/bert-base-NER" if not ENV_TEST_MODE else "dslim/bert-small-NER"
            ner_pipeline = pipeline("ner", model=model_name)
            logger.info(f"Preloaded Transformers model '{model_name}' for Lambda environment")
    except ImportError:
        logger.warning("Transformers not available")
        ENV_USE_TRANSFORMERS = False

# Ensure NLTK resources are available - always download in advance
for resource in ['stopwords', 'punkt']:
    try:
        nltk.data.find(f'corpora/{resource}' if resource == 'stopwords' else f'tokenizers/{resource}')
    except LookupError:
        nltk.download(resource, quiet=True, download_dir=str(nltk_data_path))

from nltk.corpus import stopwords


class MetadataExtractor:
    """Class for extracting metadata from document content"""
    
    def __init__(self, 
                 use_spacy: bool = ENV_USE_SPACY, 
                 use_transformers: bool = ENV_USE_TRANSFORMERS,
                 test_mode: bool = ENV_TEST_MODE,
                 memory_limit: int = ENV_MEMORY_LIMIT):
        """
        Initialize the metadata extractor.
        
        Args:
            use_spacy: Whether to use SpaCy for NER
            use_transformers: Whether to use HuggingFace transformers for NER
            test_mode: Whether to run in test mode with simplified processing
            memory_limit: Memory limit in MB (0 for no limit)
        """
        self.use_spacy = use_spacy
        self.use_transformers = use_transformers
        self.test_mode = test_mode
        self.memory_limit = memory_limit
        
        # Track initialization time
        self.init_start_time = time.time()
        
        # Initialize S3 client if available
        self.s3_client = None
        if AWS_AVAILABLE:
            try:
                self.s3_client = boto3.client('s3')
            except Exception as e:
                logger.warning(f"Failed to initialize S3 client: {e}")
        
        # Initialize NLP tools - use global preloaded models if available
        self.nlp = None
        self.ner_pipeline = None
        
        if self.use_spacy:
            try:
                # Use global model if already loaded
                if nlp is not None:
                    self.nlp = nlp
                else:
                    # Load a smaller model in test mode
                    model_name = "en_core_web_sm" if not self.test_mode else "en_core_web_sm"
                    self.nlp = spacy.load(model_name)
                logger.info(f"SpaCy model loaded successfully in {time.time() - self.init_start_time:.2f}s")
            except Exception as e:
                logger.warning(f"Failed to load SpaCy model: {e}")
                self.use_spacy = False
        
        if self.use_transformers:
            try:
                # Use global pipeline if already loaded
                if ner_pipeline is not None:
                    self.ner_pipeline = ner_pipeline
                else:
                    # Use smaller model in test mode
                    model_name = "dslim/bert-base-NER" if not self.test_mode else "dslim/bert-small-NER"
                    self.ner_pipeline = pipeline("ner", model=model_name)
                logger.info(f"Transformers NER pipeline loaded successfully in {time.time() - self.init_start_time:.2f}s")
            except Exception as e:
                logger.warning(f"Failed to load Transformers NER pipeline: {e}")
                self.use_transformers = False
        
        logger.info(f"MetadataExtractor initialized in {time.time() - self.init_start_time:.2f}s " + 
                   f"(spacy={self.use_spacy}, transformers={self.use_transformers}, test_mode={self.test_mode})")
    
    def extract_metadata(self, document_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract metadata from the document content.
        
        Args:
            document_data: Document data dictionary
            
        Returns:
            Document data with metadata extracted
        """
        start_time = time.time()
        
        try:
            text = document_data["content"]["full_text"]
            
            # Limit text size if memory limit is set
            if self.memory_limit > 0 and len(text) > self.memory_limit * 100:
                logger.warning(f"Text too large, truncating: {len(text)} chars > {self.memory_limit * 100}")
                text = text[:self.memory_limit * 100]
            
            # Use simplified processing in test mode
            if self.test_mode:
                document_data = self._extract_test_mode_metadata(document_data, text)
                processing_time = time.time() - start_time
                
                # Add processing metadata
                if "processing_metadata" not in document_data["metadata"]:
                    document_data["metadata"]["processing_metadata"] = {}
                
                document_data["metadata"]["processing_metadata"].update({
                    "test_mode": True,
                    "processing_time": processing_time,
                    "timestamp": time.time()
                })
                
                logger.info(f"Extracted test mode metadata in {processing_time:.2f}s")
                return document_data
            
            # Extract basic metadata using regex patterns
            document_data = self._extract_pattern_based_metadata(document_data, text)
            
            # Extract named entities if SpaCy is available
            if self.use_spacy:
                document_data = self._extract_spacy_entities(document_data, text)
            
            # Extract named entities if Transformers is available
            if self.use_transformers:
                document_data = self._extract_transformer_entities(document_data, text)
            
            # Identify main topics and subtopics
            document_data = self._identify_topics(document_data)
            
            # Validate and clean metadata
            document_data = self._clean_metadata(document_data)
            
            # Add processing metadata
            processing_time = time.time() - start_time
            if "processing_metadata" not in document_data["metadata"]:
                document_data["metadata"]["processing_metadata"] = {}
            
            document_data["metadata"]["processing_metadata"].update({
                "test_mode": False,
                "processing_time": processing_time,
                "memory_limited": self.memory_limit > 0,
                "spacy_used": self.use_spacy,
                "transformers_used": self.use_transformers,
                "timestamp": time.time()
            })
            
            # Report metrics if available
            if metrics and AWS_AVAILABLE:
                try:
                    metrics['put_metric']('MetadataExtractionTime', processing_time, 'Seconds')
                    metrics['put_metric']('TextLength', len(text), 'Count')
                except Exception as e:
                    logger.warning(f"Failed to report metrics: {e}")
            
            logger.info(f"Extracted metadata in {processing_time:.2f}s")
            return document_data
            
        except Exception as e:
            logger.error(f"Error extracting metadata: {e}")
            
            # Add error info to metadata
            if "processing_metadata" not in document_data["metadata"]:
                document_data["metadata"]["processing_metadata"] = {}
            
            document_data["metadata"]["processing_metadata"].update({
                "error": str(e),
                "processing_time": time.time() - start_time,
                "timestamp": time.time()
            })
            
            return document_data
    
    def extract_metadata_from_s3(self, bucket: str, key: str) -> Dict[str, Any]:
        """
        Extract metadata from document stored in S3
        
        Args:
            bucket: S3 bucket name
            key: S3 object key
            
        Returns:
            Document data with metadata extracted
        """
        if not AWS_AVAILABLE or not self.s3_client:
            raise ImportError("boto3 is required for S3 operations")
        
        try:
            # Get object from S3
            response = self.s3_client.get_object(Bucket=bucket, Key=key)
            document_json = response['Body'].read().decode('utf-8')
            document_data = json.loads(document_json)
            
            # Extract metadata
            result = self.extract_metadata(document_data)
            
            # Add S3 metadata
            if "processing_metadata" not in result["metadata"]:
                result["metadata"]["processing_metadata"] = {}
            
            result["metadata"]["processing_metadata"]["s3_source"] = {
                "bucket": bucket,
                "key": key,
                "size": response['ContentLength'],
                "last_modified": response['LastModified'].isoformat()
            }
            
            return result
            
        except ClientError as e:
            logger.error(f"Error getting object {key} from bucket {bucket}: {e}")
            raise
    
    def save_to_s3(self, document_data: Dict[str, Any], bucket: str, key: str) -> str:
        """
        Save document data to S3
        
        Args:
            document_data: Document data to save
            bucket: S3 bucket name
            key: S3 object key
            
        Returns:
            S3 URI of saved object
        """
        if not AWS_AVAILABLE or not self.s3_client:
            raise ImportError("boto3 is required for S3 operations")
        
        try:
            # Convert document to JSON
            document_json = json.dumps(document_data, default=str)
            
            # Upload to S3
            self.s3_client.put_object(
                Bucket=bucket,
                Key=key,
                Body=document_json,
                ContentType='application/json'
            )
            
            logger.info(f"Saved document to s3://{bucket}/{key}")
            return f"s3://{bucket}/{key}"
            
        except ClientError as e:
            logger.error(f"Error saving document to s3://{bucket}/{key}: {e}")
            raise
    
    def _extract_test_mode_metadata(self, document_data: Dict[str, Any], text: str) -> Dict[str, Any]:
        """
        Extract simplified metadata for test environment
        
        Args:
            document_data: Document data dictionary
            text: Text to extract from
            
        Returns:
            Document data with test metadata
        """
        # Extract very basic metadata using simplified patterns
        lines = text.splitlines()
        sample_lines = lines[:min(20, len(lines))]
        sample_text = "\n".join(sample_lines)
        
        # Basic patterns for test mode
        committee_match = re.search(r"(?i)committee:?\s+([^\n]+)", sample_text)
        country_match = re.search(r"(?i)(country|delegation):?\s+([^\n]+)", sample_text)
        topic_match = re.search(r"(?i)(topic|subject|regarding):?\s+([^\n]+)", sample_text)
        date_match = re.search(r"(\d{1,2}\/\d{1,2}\/\d{2,4})", sample_text)
        
        # Update metadata with simplified extraction
        if committee_match:
            document_data["metadata"]["committee"] = committee_match.group(1).strip()
        
        if country_match:
            document_data["metadata"]["country"] = country_match.group(2).strip()
        
        if topic_match:
            document_data["metadata"]["main_topic"] = topic_match.group(2).strip()
        
        if date_match:
            document_data["metadata"]["date"] = date_match.group(1).strip()
        
        # Extract simple topics (most frequent meaningful words)
        words = re.findall(r'\b[a-zA-Z]{5,}\b', text.lower())
        word_freq = {}
        
        for word in words:
            if word not in stopwords.words('english'):
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # Get top words by frequency
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        document_data["metadata"]["discussed_topics"] = [word for word, _ in sorted_words[:5]]
        
        return document_data
    
    def _extract_pattern_based_metadata(self, document_data: Dict[str, Any], text: str) -> Dict[str, Any]:
        """
        Extract metadata using regex patterns.
        
        Args:
            document_data: Document data dictionary
            text: Text to extract from
            
        Returns:
            Document data with pattern-based metadata extracted
        """
        # Regular expressions for common metadata patterns
        committee_patterns = [
            r"(?i)committee[:\s]+([A-Za-z0-9\s\-]+?)(?:\.|,|\n|$)",
            r"(?i)council[:\s]+([A-Za-z0-9\s\-]+?)(?:\.|,|\n|$)",
            r"(?i)assembly[:\s]+([A-Za-z0-9\s\-]+?)(?:\.|,|\n|$)"
        ]
        
        country_patterns = [
            r"(?i)delegation(?:\sof)?[:\s]+([A-Za-z\s\-]+?)(?:\.|,|\n|$)",
            r"(?i)representative(?:\sof)?[:\s]+([A-Za-z\s\-]+?)(?:\.|,|\n|$)",
            r"(?i)position(?:\sof)?[:\s]+([A-Za-z\s\-]+?)(?:\.|,|\n|$)"
        ]
        
        topic_patterns = [
            r"(?i)topic[:\s]+([^\.]+?)(?:\.|,|\n|$)",
            r"(?i)subject[:\s]+([^\.]+?)(?:\.|,|\n|$)",
            r"(?i)regarding[:\s]+([^\.]+?)(?:\.|,|\n|$)",
            r"(?i)position(?:\spaper)?(?:\son)?[:\s]+([^\.]+?)(?:\.|,|\n|$)"
        ]
        
        date_patterns = [
            r"(\d{1,2}\/\d{1,2}\/\d{2,4})",  # MM/DD/YYYY or DD/MM/YYYY
            r"(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{2,4})",  # DD Month YYYY
            r"((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{2,4})"  # Month DD, YYYY
        ]
        
        # Extract committee
        for pattern in committee_patterns:
            match = re.search(pattern, text)
            if match and match.group(1).strip():
                document_data["metadata"]["committee"] = self._clean_entity(match.group(1))
                break
        
        # Extract country
        for pattern in country_patterns:
            match = re.search(pattern, text)
            if match and match.group(1).strip():
                document_data["metadata"]["country"] = self._clean_entity(match.group(1))
                break
        
        # Extract main topic
        for pattern in topic_patterns:
            match = re.search(pattern, text)
            if match and match.group(1).strip():
                document_data["metadata"]["main_topic"] = self._clean_entity(match.group(1))
                break
        
        # Extract date
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match and match.group(1).strip():
                document_data["metadata"]["date"] = match.group(1).strip()
                break
        
        return document_data
    
    @lru_cache(maxsize=32)
    def _extract_spacy_entities(self, document_data: Dict[str, Any], text: str) -> Dict[str, Any]:
        """
        Extract named entities using SpaCy.
        
        Args:
            document_data: Document data dictionary
            text: Text to extract from
            
        Returns:
            Document data with SpaCy entities extracted
        """
        try:
            # Process text with SpaCy
            start_time = time.time()
            
            # Use a smaller text sample in AWS Lambda to reduce memory usage
            text_limit = 5000 if ENV_AWS_LAMBDA else 10000
            doc = self.nlp(text[:text_limit])  # Limit text to prevent memory issues
            
            spacy_time = time.time() - start_time
            if metrics and AWS_AVAILABLE:
                try:
                    metrics['put_metric']('SpacyProcessingTime', spacy_time, 'Seconds')
                except Exception:
                    pass
            
            # Extract and classify entities
            organizations = []
            locations = []
            dates = []
            
            for ent in doc.ents:
                if ent.label_ == "ORG":
                    organizations.append(ent.text)
                elif ent.label_ == "GPE" or ent.label_ == "LOC":
                    locations.append(ent.text)
                elif ent.label_ == "DATE":
                    dates.append(ent.text)
            
            # Update metadata if not already set
            if not document_data["metadata"]["committee"] and organizations:
                # Look for likely committee names in organizations
                committee_candidates = [org for org in organizations if any(
                    term in org.lower() for term in ["committee", "council", "assembly", "commission"]
                )]
                if committee_candidates:
                    document_data["metadata"]["committee"] = self._clean_entity(committee_candidates[0])
            
            if not document_data["metadata"]["country"] and locations:
                # Use the most frequently mentioned location as the country
                country_candidate = max(set(locations), key=locations.count)
                document_data["metadata"]["country"] = self._clean_entity(country_candidate)
            
            if not document_data["metadata"]["date"] and dates:
                document_data["metadata"]["date"] = dates[0]
            
            # Store all detected entities
            document_data["metadata"]["detected_entities"] = {
                "organizations": list(set(organizations)),
                "locations": list(set(locations)),
                "dates": list(set(dates))
            }
            
            logger.info(f"SpaCy entity extraction completed in {spacy_time:.2f}s")
            
        except Exception as e:
            logger.error(f"Error in SpaCy entity extraction: {e}")
            
            # Add error info to metadata
            if "processing_metadata" not in document_data["metadata"]:
                document_data["metadata"]["processing_metadata"] = {}
            
            document_data["metadata"]["processing_metadata"]["spacy_error"] = str(e)
        
        return document_data
    
    def _extract_transformer_entities(self, document_data: Dict[str, Any], text: str) -> Dict[str, Any]:
        """
        Extract named entities using HuggingFace Transformers.
        
        Args:
            document_data: Document data dictionary
            text: Text to extract from
            
        Returns:
            Document data with transformer entities extracted
        """
        try:
            start_time = time.time()
            
            # Process text with the NER pipeline
            # We'll process in chunks to handle long documents
            # Use smaller chunks in AWS Lambda
            max_chunk_length = 256 if ENV_AWS_LAMBDA else 512
            max_chunks = 10 if ENV_AWS_LAMBDA else 20
            
            chunks = self._split_text_into_chunks(text, max_length=max_chunk_length)
            # Limit the number of chunks to process
            chunks = chunks[:max_chunks]
            
            all_entities = []
            for i, chunk in enumerate(chunks):
                chunk_start = time.time()
                entities = self.ner_pipeline(chunk)
                all_entities.extend(entities)
                logger.debug(f"Processed chunk {i+1}/{len(chunks)} in {time.time() - chunk_start:.2f}s")
            
            transformers_time = time.time() - start_time
            if metrics and AWS_AVAILABLE:
                try:
                    metrics['put_metric']('TransformersProcessingTime', transformers_time, 'Seconds')
                    metrics['put_metric']('ChunksProcessed', len(chunks), 'Count')
                except Exception:
                    pass
            
            # Combine entities with the same label that appear consecutively
            combined_entities = self._combine_consecutive_entities(all_entities)
            
            # Organize by entity type
            entity_groups = {}
            for entity in combined_entities:
                entity_type = entity["entity"]
                entity_text = entity["word"]
                if entity_type not in entity_groups:
                    entity_groups[entity_type] = []
                entity_groups[entity_type].append(entity_text)
            
            # Map entity types to metadata fields
            if "B-ORG" in entity_groups and not document_data["metadata"]["committee"]:
                committee_candidates = [org for org in entity_groups["B-ORG"] if any(
                    term in org.lower() for term in ["committee", "council", "assembly", "commission"]
                )]
                if committee_candidates:
                    document_data["metadata"]["committee"] = self._clean_entity(committee_candidates[0])
            
            if "B-LOC" in entity_groups and not document_data["metadata"]["country"]:
                document_data["metadata"]["country"] = self._clean_entity(entity_groups["B-LOC"][0])
            
            # Store transformer detected entities
            document_data["metadata"]["transformer_entities"] = entity_groups
            
            logger.info(f"Transformer entity extraction completed in {transformers_time:.2f}s")
            
        except Exception as e:
            logger.error(f"Error in Transformer entity extraction: {e}")
            
            # Add error info to metadata
            if "processing_metadata" not in document_data["metadata"]:
                document_data["metadata"]["processing_metadata"] = {}
            
            document_data["metadata"]["processing_metadata"]["transformer_error"] = str(e)
        
        return document_data
    
    def _identify_topics(self, document_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Identify topics discussed in the document.
        
        Args:
            document_data: Document data dictionary
            
        Returns:
            Document data with topics identified
        """
        try:
            start_time = time.time()
            text = document_data["content"]["full_text"]
            
            # Get stopwords
            stop_words = set(stopwords.words('english'))
            
            # Add additional stopwords relevant to position papers/speeches
            additional_stops = [
                'committee', 'council', 'delegation', 'representative', 'position',
                'paper', 'speech', 'delegate', 'country', 'international', 'topic',
                'issue', 'problem', 'solution', 'resolution', 'draft', 'proposal',
                'thank', 'you', 'chair', 'president', 'excellency', 'honorable'
            ]
            stop_words.update(additional_stops)
            
            # Use simpler approach in Lambda environment to reduce memory usage
            if ENV_AWS_LAMBDA:
                # Simple word frequency approach
                words = text.lower().split()
                word_freq = {}
                for word in words:
                    if len(word) > 4 and word not in stop_words:
                        word_freq[word] = word_freq.get(word, 0) + 1
                
                # Get top words by frequency
                sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
                document_data["metadata"]["discussed_topics"] = [word for word, freq in sorted_words[:5]]
                
                topics_time = time.time() - start_time
                logger.info(f"Extracted topics using simple frequency in {topics_time:.2f}s")
                return document_data
            
            # Create vectorizer for keywords/topics
            from sklearn.feature_extraction.text import TfidfVectorizer
            vectorizer = TfidfVectorizer(
                max_features=10,
                stop_words=stop_words,
                ngram_range=(1, 2),
                min_df=2
            )
            
            # Generate tf-idf matrix
            tfidf_matrix = vectorizer.fit_transform([text])
            
            # Get feature names
            feature_names = vectorizer.get_feature_names_out()
            
            # Get tf-idf scores
            scores = tfidf_matrix.toarray()[0]
            
            # Sort by score and get top keywords/phrases
            sorted_items = [(feature_names[i], scores[i]) for i in range(len(feature_names))]
            sorted_items.sort(key=lambda x: x[1], reverse=True)
            
            # Extract top topics
            document_data["metadata"]["discussed_topics"] = [
                item[0] for item in sorted_items[:5] if item[1] > 0.05
            ]
            
            # If we couldn't extract enough topics, try with paragraphs
            if len(document_data["metadata"]["discussed_topics"]) < 3:
                # Get text from the first few paragraphs where topics are often mentioned
                if document_data["content"]["paragraphs"]:
                    intro_text = " ".join(document_data["content"]["paragraphs"][:3])
                    
                    # Use only single words for better topic extraction from intro
                    intro_vectorizer = TfidfVectorizer(
                        max_features=10,
                        stop_words=stop_words,
                        ngram_range=(1, 1)
                    )
                    
                    intro_matrix = intro_vectorizer.fit_transform([intro_text])
                    intro_features = intro_vectorizer.get_feature_names_out()
                    intro_scores = intro_matrix.toarray()[0]
                    
                    intro_items = [(intro_features[i], intro_scores[i]) for i in range(len(intro_features))]
                    intro_items.sort(key=lambda x: x[1], reverse=True)
                    
                    # Add these topics
                    intro_topics = [item[0] for item in intro_items[:5] if item[1] > 0.05]
                    document_data["metadata"]["discussed_topics"].extend(intro_topics)
                    
                    # Remove duplicates
                    document_data["metadata"]["discussed_topics"] = list(set(document_data["metadata"]["discussed_topics"]))
            
            topics_time = time.time() - start_time
            if metrics and AWS_AVAILABLE:
                try:
                    metrics['put_metric']('TopicExtractionTime', topics_time, 'Seconds')
                except Exception:
                    pass
                
            logger.info(f"Topic identification completed in {topics_time:.2f}s")
            
        except Exception as e:
            logger.error(f"Error in topic identification: {e}")
            
            # Fallback to simple word frequency for topic extraction
            words = text.lower().split()
            word_freq = {}
            for word in words:
                if len(word) > 4 and word not in stop_words:  # Only count meaningful words
                    word_freq[word] = word_freq.get(word, 0) + 1
            
            # Get top words by frequency
            sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
            document_data["metadata"]["discussed_topics"] = [word for word, freq in sorted_words[:5]]
            
            # Add error info to metadata
            if "processing_metadata" not in document_data["metadata"]:
                document_data["metadata"]["processing_metadata"] = {}
            
            document_data["metadata"]["processing_metadata"]["topic_error"] = str(e)
        
        return document_data
    
    def _clean_metadata(self, document_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clean and validate extracted metadata.
        
        Args:
            document_data: Document data dictionary
            
        Returns:
            Document data with cleaned metadata
        """
        # Clean and validate committee
        if document_data["metadata"]["committee"]:
            document_data["metadata"]["committee"] = self._clean_entity(document_data["metadata"]["committee"])
        
        # Clean and validate country
        if document_data["metadata"]["country"]:
            document_data["metadata"]["country"] = self._clean_entity(document_data["metadata"]["country"])
        
        # Clean and validate main topic
        if document_data["metadata"]["main_topic"]:
            document_data["metadata"]["main_topic"] = self._clean_entity(document_data["metadata"]["main_topic"])
        
        # Standardize date format if possible
        if document_data["metadata"]["date"]:
            try:
                # Try to parse and standardize the date
                parsed_date = self._parse_date(document_data["metadata"]["date"])
                if parsed_date:
                    document_data["metadata"]["date"] = parsed_date.strftime("%Y-%m-%d")
            except Exception as e:
                logger.warning(f"Could not standardize date format: {e}")
        
        # Ensure unique topics
        if document_data["metadata"]["discussed_topics"]:
            # Remove duplicates and ensure all topics are strings
            topics = list(set(str(topic) for topic in document_data["metadata"]["discussed_topics"]))
            # Sort by length to prioritize longer, more informative phrases
            topics.sort(key=len, reverse=True)
            document_data["metadata"]["discussed_topics"] = topics
        
        return document_data
    
    def _clean_entity(self, entity: str) -> str:
        """
        Clean an extracted entity string.
        
        Args:
            entity: Entity text to clean
            
        Returns:
            Cleaned entity text
        """
        # Remove leading/trailing punctuation and whitespace
        entity = re.sub(r'^[\s\.,;:"\']+|[\s\.,;:"\']+$', '', entity)
        
        # Replace multiple spaces with single space
        entity = re.sub(r'\s+', ' ', entity)
        
        return entity.strip()
    
    def _parse_date(self, date_str: str) -> Optional[datetime.datetime]:
        """
        Parse a date string into a datetime object.
        
        Args:
            date_str: Date string to parse
            
        Returns:
            Datetime object or None if parsing fails
        """
        date_formats = [
            "%m/%d/%Y", "%d/%m/%Y",  # MM/DD/YYYY or DD/MM/YYYY
            "%m/%d/%y", "%d/%m/%y",  # MM/DD/YY or DD/MM/YY
            "%d %B %Y", "%B %d, %Y", "%B %d %Y"  # DD Month YYYY or Month DD, YYYY
        ]
        
        for fmt in date_formats:
            try:
                return datetime.datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        return None
    
    def _split_text_into_chunks(self, text: str, max_length: int = 512) -> List[str]:
        """
        Split text into chunks for processing by transformer models.
        
        Args:
            text: Text to split
            max_length: Maximum chunk length
            
        Returns:
            List of text chunks
        """
        # Split by sentences to avoid cutting in the middle of entities
        sentences = nltk.sent_tokenize(text)
        
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            # If adding this sentence would exceed max_length
            if len(current_chunk) + len(sentence) > max_length:
                # Add current chunk to the list
                if current_chunk:
                    chunks.append(current_chunk)
                # Start a new chunk
                current_chunk = sentence
            else:
                # Add sentence to current chunk
                if current_chunk:
                    current_chunk += " " + sentence
                else:
                    current_chunk = sentence
        
        # Add the last chunk if it exists
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
    def _combine_consecutive_entities(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Combine consecutive entities with the same label.
        
        Args:
            entities: List of entity dictionaries
            
        Returns:
            List of combined entity dictionaries
        """
        if not entities:
            return []
        
        combined = []
        current_entity = None
        
        for entity in entities:
            if not current_entity:
                current_entity = entity.copy()
                continue
            
            # Check if this entity continues the previous one
            if (entity["entity"].startswith("I-") and 
                current_entity["entity"].startswith("B-") and
                entity["entity"][2:] == current_entity["entity"][2:]):
                # Extend the current entity
                current_entity["word"] += " " + entity["word"].lstrip("##")
                current_entity["end"] = entity["end"]
            else:
                # Add the current entity to the result and start a new one
                combined.append(current_entity)
                current_entity = entity.copy()
        
        # Add the last entity
        if current_entity:
            combined.append(current_entity)
        
        return combined


# Create sample test data for testing purposes
def create_test_document() -> Dict[str, Any]:
    """
    Create a sample document for testing.
    
    Returns:
        Sample document data
    """
    return {
        "metadata": {
            "committee": "",
            "country": "",
            "main_topic": "",
            "date": "",
            "discussed_topics": []
        },
        "content": {
            "full_text": """
            POSITION PAPER
            Committee: United Nations Security Council
            Topic: Nuclear Non-Proliferation in Middle East
            Country: United States of America
            
            The United States delegation to the United Nations Security Council expresses its commitment to addressing the critical issue of nuclear non-proliferation in the Middle East. As of January 15, 2023, our position remains focused on promoting a weapons-free zone while ensuring regional security and stability.
            
            Nuclear proliferation poses an existential threat to peace in the region. The United States supports the following key principles:
            1. Strengthening the Non-Proliferation Treaty framework
            2. Encouraging diplomatic solutions to regional tensions
            3. Implementing robust verification mechanisms
            4. Supporting peaceful nuclear energy development
            
            The delegation believes that international cooperation and multilateral agreements represent the best path forward for achieving lasting peace and security in the Middle East.
            """,
            "paragraphs": [
                "POSITION PAPER",
                "Committee: United Nations Security Council",
                "Topic: Nuclear Non-Proliferation in Middle East",
                "Country: United States of America",
                "The United States delegation to the United Nations Security Council expresses its commitment to addressing the critical issue of nuclear non-proliferation in the Middle East. As of January 15, 2023, our position remains focused on promoting a weapons-free zone while ensuring regional security and stability.",
                "Nuclear proliferation poses an existential threat to peace in the region. The United States supports the following key principles:",
                "1. Strengthening the Non-Proliferation Treaty framework",
                "2. Encouraging diplomatic solutions to regional tensions",
                "3. Implementing robust verification mechanisms",
                "4. Supporting peaceful nuclear energy development",
                "The delegation believes that international cooperation and multilateral agreements represent the best path forward for achieving lasting peace and security in the Middle East."
            ]
        }
    }


# Testing function if run directly
if __name__ == "__main__":
    import json
    import sys
    import argparse
    
    # Parse arguments
    parser = argparse.ArgumentParser(description='Extract metadata from documents')
    parser.add_argument('--input', help='Input file path or S3 URI (s3://bucket/key)')
    parser.add_argument('--output', help='Output file path or S3 URI (s3://bucket/key)')
    parser.add_argument('--test-mode', action='store_true', help='Run in test mode with simplified processing')
    parser.add_argument('--test-data', action='store_true', help='Use sample test data')
    parser.add_argument('--memory-limit', type=int, default=0, help='Memory limit in MB (0 for no limit)')
    parser.add_argument('--aws', action='store_true', help='Force AWS mode for S3 operations')
    parser.add_argument('--no-spacy', action='store_true', help='Disable SpaCy')
    parser.add_argument('--no-transformers', action='store_true', help='Disable Transformers')
    args = parser.parse_args()
    
    try:
        # Initialize extractor
        extractor = MetadataExtractor(
            use_spacy=not args.no_spacy, 
            use_transformers=not args.no_transformers,
            test_mode=args.test_mode,
            memory_limit=args.memory_limit
        )
        
        # Process the document
        if args.test_data:
            # Use sample test data
            print("Using sample test data")
            document_data = create_test_document()
            result = extractor.extract_metadata(document_data)
            
            # Print the result
            print("\nExtracted Metadata:")
            for key, value in result["metadata"].items():
                if key not in ["detected_entities", "transformer_entities", "processing_metadata"]:
                    print(f"  {key}: {value}")
            
            # Save to output if specified
            if args.output:
                if args.output.startswith('s3://') and (AWS_AVAILABLE or args.aws):
                    # Parse S3 URI
                    s3_path = args.output[5:]  # Remove "s3://"
                    bucket, key = s3_path.split('/', 1)
                    
                    # Save to S3
                    s3_uri = extractor.save_to_s3(result, bucket, key)
                    print(f"Saved result to {s3_uri}")
                else:
                    # Save to local file
                    with open(args.output, 'w', encoding='utf-8') as f:
                        json.dump(result, f, indent=2, ensure_ascii=False)
                    print(f"Saved result to {args.output}")
            
        elif args.input:
            if args.input.startswith('s3://') and (AWS_AVAILABLE or args.aws):
                # Parse S3 URI
                s3_path = args.input[5:]  # Remove "s3://"
                bucket, key = s3_path.split('/', 1)
                
                print(f"Extracting metadata from S3: s3://{bucket}/{key}")
                result = extractor.extract_metadata_from_s3(bucket, key)
                
                # Save to output if specified
                if args.output:
                    if args.output.startswith('s3://'):
                        # Parse S3 URI
                        output_s3_path = args.output[5:]  # Remove "s3://"
                        output_bucket, output_key = output_s3_path.split('/', 1)
                        
                        # Save to S3
                        s3_uri = extractor.save_to_s3(result, output_bucket, output_key)
                        print(f"Saved result to {s3_uri}")
                    else:
                        # Save to local file
                        with open(args.output, 'w', encoding='utf-8') as f:
                            json.dump(result, f, indent=2, ensure_ascii=False)
                        print(f"Saved result to {args.output}")
                else:
                    # Save back to input location
                    s3_uri = extractor.save_to_s3(result, bucket, key)
                    print(f"Updated document at {s3_uri}")
                
                # Print the result
                print("\nExtracted Metadata:")
                for key, value in result["metadata"].items():
                    if key not in ["detected_entities", "transformer_entities", "processing_metadata"]:
                        print(f"  {key}: {value}")
                
            else:
                # Local file
                with open(args.input, 'r', encoding='utf-8') as f:
                    document_data = json.load(f)
                
                print(f"Extracting metadata from {args.input}")
                result = extractor.extract_metadata(document_data)
                
                # Save the result
                output_path = args.output if args.output else args.input
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)
                
                print(f"Successfully extracted metadata and updated {output_path}")
                
                # Print the result
                print("\nExtracted Metadata:")
                for key, value in result["metadata"].items():
                    if key not in ["detected_entities", "transformer_entities", "processing_metadata"]:
                        print(f"  {key}: {value}")
        
        else:
            print("No input specified. Use --input or --test-data")
            parser.print_help()
    
    except Exception as e:
        print(f"Error extracting metadata: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


# AWS Lambda handler
def lambda_handler(event, context):
    """
    AWS Lambda handler for metadata extraction
    
    Args:
        event: Lambda event
        context: Lambda context
        
    Returns:
        Lambda response
    """
    # Configure logging for Lambda
    if ENV_AWS_LAMBDA:
        logger.setLevel(logging.INFO)
    
    # Log event details (excluding large payloads)
    event_info = {k: v for k, v in event.items() if k != 'document_data'}
    logger.info(f"Processing Lambda event: {json.dumps(event_info)}")
    
    start_time = time.time()
    
    try:
        # Get configuration from event
        test_mode = event.get('test_mode', ENV_TEST_MODE)
        memory_limit = int(event.get('memory_limit', ENV_MEMORY_LIMIT))
        use_spacy = event.get('use_spacy', ENV_USE_SPACY)
        use_transformers = event.get('use_transformers', ENV_USE_TRANSFORMERS)
        
        # Initialize extractor
        extractor = MetadataExtractor(
            use_spacy=use_spacy, 
            use_transformers=use_transformers,
            test_mode=test_mode,
            memory_limit=memory_limit
        )
        
        # Extract metadata based on input type
        result = None
        
        if 'document_data' in event:
            # Direct document data input
            result = extractor.extract_metadata(event['document_data'])
            
        elif 's3_bucket' in event and 's3_key' in event:
            # S3 input
            result = extractor.extract_metadata_from_s3(event['s3_bucket'], event['s3_key'])
            
            # Save to S3 if output path specified
            if 'output_s3_key' in event:
                s3_uri = extractor.save_to_s3(
                    result, 
                    event.get('output_s3_bucket', event['s3_bucket']),
                    event['output_s3_key']
                )
                result["processing_metadata"]["output_uri"] = s3_uri
            
        elif 'test_data' in event and event['test_data']:
            # Use sample test data
            document_data = create_test_document()
            result = extractor.extract_metadata(document_data)
            
        else:
            # Invalid input
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Invalid input. Must provide document_data, S3 path, or test_data flag.'
                })
            }
        
        # Add Lambda processing metadata
        processing_time = time.time() - start_time
        if "processing_metadata" not in result["metadata"]:
            result["metadata"]["processing_metadata"] = {}
        
        result["metadata"]["processing_metadata"].update({
            'lambda_processing_time': processing_time,
            'aws_request_id': context.aws_request_id if context else None,
            'test_mode': test_mode,
            'use_spacy': use_spacy,
            'use_transformers': use_transformers,
            'timestamp': time.time()
        })
        
        # Report metrics
        if metrics:
            try:
                metrics['put_metric']('LambdaProcessingTime', processing_time, 'Seconds')
                metrics['put_metric']('LambdaInvocations', 1, 'Count')
            except Exception as e:
                logger.warning(f"Failed to report Lambda metrics: {e}")
        
        # Return success
        return {
            'statusCode': 200,
            'body': json.dumps(result, default=str)
        }
    
    except Exception as e:
        # Log error
        logger.error(f"Error in Lambda handler: {str(e)}", exc_info=True)
        
        # Report error metric
        if metrics:
            try:
                metrics['put_metric']('LambdaErrors', 1, 'Count')
            except Exception:
                pass
        
        # Return error response
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'processing_metadata': {
                    'error': True,
                    'lambda_processing_time': time.time() - start_time,
                    'aws_request_id': context.aws_request_id if context else None,
                    'timestamp': time.time()
                }
            })
        }
