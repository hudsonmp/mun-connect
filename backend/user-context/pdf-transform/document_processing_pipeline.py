#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Document Processing Pipeline

This module coordinates the entire document processing pipeline, including PDF extraction,
metadata extraction, linguistic analysis, BERT formatting, and argumentation analysis.
Supports serverless execution in AWS Lambda and containerized execution in ECS.
"""

import os
import json
import logging
import time
import tempfile
import traceback
import uuid
from typing import Dict, List, Any, Optional, Tuple, Union, BinaryIO
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache

# Import configuration
from config import (
    config_handler, ENV_TEST_MODE, IS_LAMBDA, IS_PRODUCTION,
    PROCESSING_OPTIONS, S3_CONFIG, ENV_S3_BUCKET, IAM_REQUIRED_PERMISSIONS,
    OUTPUT_DIR, TEMP_DIR, MODELS, TEST_CONFIG
)

# Import processors - lazy loaded to improve cold start times
pdf_processor = None
metadata_extractor = None
bert_formatter = None
linguistic_features_extractor = None
argumentation_analyzer = None

# AWS specific imports
try:
    import boto3
    AWS_AVAILABLE = True
except ImportError:
    AWS_AVAILABLE = False

# Configure logging
logger = logging.getLogger(__name__)

# Import SQS message handling for large documents
try:
    from aws_helpers import SQSHelper, LambdaHelper, check_aws_permissions
    SQS_AVAILABLE = True
except ImportError:
    SQS_AVAILABLE = False
    logger.warning("SQS helper not available - large document queueing disabled")

class DocumentProcessingPipeline:
    """Main pipeline for processing documents with AWS Lambda/ECS support"""
    
    def __init__(
        self,
        use_markdown: bool = PROCESSING_OPTIONS["use_markdown"],
        use_spacy: bool = PROCESSING_OPTIONS["use_spacy"],
        use_transformers: bool = PROCESSING_OPTIONS["use_transformers"],
        parallel_processing: bool = PROCESSING_OPTIONS["parallel_processing"],
        bert_model: str = MODELS["bert"]["default"],
        component_model: str = MODELS["argument_component"]["default"],
        relation_model: str = MODELS["argument_relation"]["default"],
        reasoning_model: str = MODELS["reasoning"]["default"],
        use_gpu: bool = PROCESSING_OPTIONS["use_gpu"],
        output_dir: Optional[str] = None,
        lazy_loading: bool = IS_LAMBDA,  # Use lazy loading by default in Lambda to improve cold start
        s3_bucket: Optional[str] = ENV_S3_BUCKET,
        use_sqs_for_large_docs: bool = SQS_AVAILABLE and not ENV_TEST_MODE,
        max_workers: int = PROCESSING_OPTIONS["max_workers"]
    ):
        """
        Initialize the document processing pipeline.
        
        Args:
            use_markdown: Whether to convert PDFs to markdown
            use_spacy: Whether to use SpaCy for entity extraction
            use_transformers: Whether to use HuggingFace transformers
            parallel_processing: Whether to use parallel processing
            bert_model: BERT model to use for embeddings
            component_model: Model for argument component detection
            relation_model: Model for argument relation classification
            reasoning_model: Model for reasoning pattern classification
            use_gpu: Whether to use GPU for processing
            output_dir: Directory to save output files
            lazy_loading: Whether to lazy load NLP models (reduces cold start time)
            s3_bucket: S3 bucket for storage
            use_sqs_for_large_docs: Whether to use SQS for processing large documents
            max_workers: Maximum number of worker threads for parallel processing
        """
        self.use_markdown = use_markdown
        self.use_spacy = use_spacy
        self.use_transformers = use_transformers
        self.parallel_processing = parallel_processing
        self.use_gpu = use_gpu and not ENV_TEST_MODE  # Disable GPU in test mode
        self.max_workers = max_workers
        
        # Set models
        self.bert_model = bert_model
        self.component_model = component_model
        self.relation_model = relation_model
        self.reasoning_model = reasoning_model
        
        # Set AWS configuration
        self.s3_bucket = s3_bucket
        self.use_s3 = s3_bucket is not None and AWS_AVAILABLE
        self.use_sqs = use_sqs_for_large_docs
        self.lazy_loading = lazy_loading
        
        # Set up output directory
        self.output_dir = output_dir or OUTPUT_DIR
        
        # Set up temp directory for working with files
        self.temp_dir = TEMP_DIR
        os.makedirs(self.temp_dir, exist_ok=True)
        
        # Initialize SQS helper if needed
        self.sqs_helper = None
        if self.use_sqs:
            try:
                self.sqs_helper = SQSHelper()
                logger.info("SQS helper initialized for large document processing")
            except Exception as e:
                logger.warning(f"Failed to initialize SQS helper: {str(e)}")
                self.use_sqs = False
        
        # Check AWS permissions if using AWS services
        if self.use_s3 or self.use_sqs:
            self._check_aws_permissions()
        
        # Initialize processors (only if not using lazy loading)
        if not self.lazy_loading:
            self._initialize_processors()
            logger.info("All processors initialized")
        else:
            logger.info("Using lazy loading for processors - will initialize on first use")
    
    def _check_aws_permissions(self) -> None:
        """Check if the required AWS permissions are available"""
        if not AWS_AVAILABLE:
            return
        
        try:
            required_perms = []
            if self.use_s3:
                required_perms.extend(["s3:GetObject", "s3:PutObject", "s3:ListBucket"])
            if self.use_sqs:
                required_perms.extend(["sqs:SendMessage", "sqs:ReceiveMessage", "sqs:DeleteMessage"])
            
            has_permissions = check_aws_permissions(required_perms)
            if not has_permissions:
                logger.warning("Missing some AWS permissions - functionality may be limited")
        except Exception as e:
            logger.warning(f"Failed to check AWS permissions: {str(e)}")
    
    def _initialize_processors(self) -> None:
        """Initialize all document processors"""
        global pdf_processor, metadata_extractor, bert_formatter
        global linguistic_features_extractor, argumentation_analyzer
        
        logger.info("Initializing document processing pipeline...")
        
        # Initialize or reuse global processors
        if pdf_processor is None:
            from pdf_processor import PDFProcessor
            pdf_processor = PDFProcessor(use_markdown=self.use_markdown)
        self.pdf_processor = pdf_processor
        logger.info("PDF processor initialized")
        
        if metadata_extractor is None:
            from metadata_extractor import MetadataExtractor
            metadata_extractor = MetadataExtractor(
                use_spacy=self.use_spacy, 
                use_transformers=self.use_transformers
            )
        self.metadata_extractor = metadata_extractor
        logger.info("Metadata extractor initialized")
        
        if bert_formatter is None:
            from bert_formatter import BertFormatter
            bert_formatter = BertFormatter(model_name=self.bert_model)
        self.bert_formatter = bert_formatter
        logger.info("BERT formatter initialized")
        
        if linguistic_features_extractor is None:
            from linguistic_features import LinguisticFeaturesExtractor
            linguistic_features_extractor = LinguisticFeaturesExtractor()
        self.linguistic_features_extractor = linguistic_features_extractor
        logger.info("Linguistic features extractor initialized")
        
        if argumentation_analyzer is None:
            from argumentation_analyzer import ArgumentationAnalyzer
            argumentation_analyzer = ArgumentationAnalyzer(
                component_model=self.component_model,
                relation_model=self.relation_model,
                reasoning_model=self.reasoning_model,
                use_gpu=self.use_gpu
            )
        self.argumentation_analyzer = argumentation_analyzer
        logger.info("Argumentation analyzer initialized")
    
    def _get_s3_path(self, path: str) -> Tuple[str, str]:
        """
        Convert a path to an S3 path.
        
        Args:
            path: Local path or S3 key
            
        Returns:
            Tuple of (bucket, key)
        """
        if path.startswith('s3://'):
            # Extract bucket and key from s3:// URL
            parts = path[5:].split('/', 1)
            if len(parts) == 1:
                bucket, key = parts[0], ''
            else:
                bucket, key = parts
            return bucket, key
        
        # Use default bucket with key
        return self.s3_bucket, path
    
    def _download_from_s3(self, s3_path: str, local_path: Optional[str] = None) -> str:
        """
        Download a file from S3.
        
        Args:
            s3_path: S3 path (can be s3://bucket/key or just key)
            local_path: Local path to save to (if None, use temp file)
            
        Returns:
            Local path where file was saved
        """
        if not self.use_s3:
            return s3_path  # If not using S3, assume s3_path is local
        
        try:
            bucket, key = self._get_s3_path(s3_path)
            
            # Generate local path if not provided
            if not local_path:
                filename = os.path.basename(key)
                local_path = os.path.join(self.temp_dir, f"{uuid.uuid4().hex}_{filename}")
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            # Download file
            logger.info(f"Downloading {bucket}/{key} to {local_path}")
            s3 = boto3.client('s3')
            s3.download_file(bucket, key, local_path)
            
            return local_path
        except Exception as e:
            logger.error(f"Error downloading from S3: {str(e)}")
            if ENV_TEST_MODE and TEST_CONFIG["mock_s3"]:
                # In test mode with mock S3, just return the original path
                return s3_path
            raise
    
    def _upload_to_s3(self, local_path: str, s3_key: Optional[str] = None) -> str:
        """
        Upload a file to S3.
        
        Args:
            local_path: Local path to upload
            s3_key: S3 key to upload to (if None, use basename of local_path)
            
        Returns:
            S3 path where file was uploaded
        """
        if not self.use_s3:
            return local_path  # If not using S3, just return local path
        
        try:
            # Generate S3 key if not provided
            if not s3_key:
                filename = os.path.basename(local_path)
                s3_key = os.path.join(S3_CONFIG["output_prefix"], filename)
            
            logger.info(f"Uploading {local_path} to {self.s3_bucket}/{s3_key}")
            s3 = boto3.client('s3')
            s3.upload_file(local_path, self.s3_bucket, s3_key)
            
            return f"s3://{self.s3_bucket}/{s3_key}"
        except Exception as e:
            logger.error(f"Error uploading to S3: {str(e)}")
            if ENV_TEST_MODE and TEST_CONFIG["mock_s3"]:
                # In test mode with mock S3, just return the original path
                return local_path
            raise
    
    def _maybe_queue_large_document(self, pdf_path: str, document_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Check if a document is too large for Lambda processing and queue it if needed.
        
        Args:
            pdf_path: Path to the PDF file
            document_type: Type of document
            
        Returns:
            Queue message response if document was queued, None otherwise
        """
        if not self.use_sqs or not IS_LAMBDA:
            return None
        
        try:
            # Check file size (Lambda has 512MB tmp storage, but we'll use a lower threshold)
            threshold_mb = 50
            
            # For S3 paths, get file size from S3
            if pdf_path.startswith('s3://'):
                bucket, key = self._get_s3_path(pdf_path)
                s3 = boto3.client('s3')
                response = s3.head_object(Bucket=bucket, Key=key)
                size_mb = response['ContentLength'] / (1024 * 1024)
            else:
                # For local paths, get file size from filesystem
                size_mb = os.path.getsize(pdf_path) / (1024 * 1024)
            
            if size_mb > threshold_mb:
                logger.info(f"Document {pdf_path} is {size_mb:.2f}MB, exceeds threshold of {threshold_mb}MB. Queueing for batch processing.")
                
                # Queue document for processing
                message = {
                    "pdf_path": pdf_path,
                    "document_type": document_type,
                    "queued_at": time.time()
                }
                
                response = self.sqs_helper.send_message(message)
                
                return {
                    "queued": True,
                    "message_id": response["MessageId"],
                    "queue_url": self.sqs_helper.queue_url,
                    "pdf_path": pdf_path,
                    "document_type": document_type,
                    "status": "queued"
                }
        
        except Exception as e:
            logger.warning(f"Failed to check document size or queue document: {str(e)}")
        
        return None
    
    def process_document(self, pdf_path: str, document_type: Optional[str] = None) -> Tuple[str, Dict[str, Any]]:
        """
        Process a single document through the entire pipeline.
        
        Args:
            pdf_path: Path to the PDF file (local path or S3 URL)
            document_type: Type of document (position_paper, speech, etc.)
            
        Returns:
            Tuple of (output path, processed document data)
        """
        # Initialize processors if using lazy loading
        if self.lazy_loading and not hasattr(self, 'pdf_processor'):
            self._initialize_processors()
        
        # Check if document should be queued for batch processing
        queued = self._maybe_queue_large_document(pdf_path, document_type)
        if queued:
            return "", queued
        
        # Download from S3 if needed
        local_pdf_path = pdf_path
        if self.use_s3 and (pdf_path.startswith('s3://') or '/' not in pdf_path):
            local_pdf_path = self._download_from_s3(pdf_path)
            logger.info(f"Downloaded {pdf_path} to {local_pdf_path}")
        
        try:
            logger.info(f"Processing document: {pdf_path}")
            start_time = time.time()
            
            # Step 1: Extract text from PDF
            logger.info("Step 1: Extracting text from PDF")
            document_data = self.pdf_processor.process_pdf(local_pdf_path, document_type)
            logger.info(f"Text extraction completed. Extracted {len(document_data['content']['sentences'])} sentences")
            
            # Step 2: Extract metadata
            logger.info("Step 2: Extracting metadata")
            document_data = self.metadata_extractor.extract_metadata(document_data)
            logger.info("Metadata extraction completed")
            
            # Step 3: Format for BERT
            logger.info("Step 3: Formatting for BERT")
            document_data = self.bert_formatter.format_for_bert(document_data)
            logger.info(f"BERT formatting completed. Created {document_data['bert_friendly']['segment_count']} segments")
            
            # Step 4: Extract linguistic features
            logger.info("Step 4: Extracting linguistic features")
            document_data["linguistic_features"] = self.linguistic_features_extractor.extract_features(
                document_data["content"]["full_text"]
            )
            
            # Process segments if available
            if "segments" in document_data["bert_friendly"]:
                document_data["bert_friendly"]["segments"] = self.linguistic_features_extractor.extract_segment_features(
                    document_data["bert_friendly"]["segments"]
                )
            logger.info("Linguistic feature extraction completed")
            
            # Step 5: Analyze argumentation
            logger.info("Step 5: Analyzing argumentation")
            document_data = self.argumentation_analyzer.analyze_argumentation(document_data)
            logger.info("Argumentation analysis completed")
            
            # Add processing metadata
            document_data["processing_metadata"] = {
                "processing_time": time.time() - start_time,
                "timestamp": time.time(),
                "original_path": pdf_path,
                "document_type": document_type,
                "environment": "lambda" if IS_LAMBDA else "container" if os.environ.get("CONTAINER_MODE") else "local"
            }
            
            # Generate output filename
            base_name = os.path.splitext(os.path.basename(local_pdf_path))[0]
            output_filename = f"{base_name}_processed.json"
            
            # Create local output path
            local_output_path = os.path.join(self.temp_dir, output_filename)
            
            # Save locally first
            with open(local_output_path, 'w', encoding='utf-8') as f:
                json.dump(document_data, f, indent=2, ensure_ascii=False)
            
            # Upload to S3 if needed
            if self.use_s3:
                s3_output_key = os.path.join(S3_CONFIG["output_prefix"], output_filename)
                output_path = self._upload_to_s3(local_output_path, s3_output_key)
            else:
                # If not using S3, move file to output directory
                final_output_path = os.path.join(self.output_dir, output_filename)
                os.makedirs(os.path.dirname(final_output_path), exist_ok=True)
                
                # Copy the file (don't move, as it might be needed for further processing)
                with open(local_output_path, 'r') as src, open(final_output_path, 'w') as dst:
                    dst.write(src.read())
                
                output_path = final_output_path
            
            end_time = time.time()
            logger.info(f"Document processing completed in {end_time - start_time:.2f} seconds")
            logger.info(f"Results saved to {output_path}")
            
            return output_path, document_data
            
        except Exception as e:
            logger.error(f"Error processing document {pdf_path}: {str(e)}")
            logger.error(traceback.format_exc())
            raise
        finally:
            # Clean up temporary file if downloaded from S3
            if self.use_s3 and local_pdf_path != pdf_path and os.path.exists(local_pdf_path):
                try:
                    os.remove(local_pdf_path)
                    logger.debug(f"Removed temporary file {local_pdf_path}")
                except Exception as e:
                    logger.warning(f"Failed to remove temporary file {local_pdf_path}: {str(e)}")
    
    def process_multiple_documents(self, pdf_paths: List[str], document_types: Optional[List[str]] = None) -> List[Tuple[str, Dict[str, Any]]]:
        """
        Process multiple documents.
        
        Args:
            pdf_paths: List of PDF file paths (local paths or S3 URLs)
            document_types: Optional list of document types
            
        Returns:
            List of tuples (output path, processed document data)
        """
        logger.info(f"Processing {len(pdf_paths)} documents")
        
        # Prepare document types if provided
        if document_types and len(document_types) != len(pdf_paths):
            raise ValueError("If document_types is provided, it must have the same length as pdf_paths")
        
        doc_types = document_types or [None] * len(pdf_paths)
        
        if self.parallel_processing and len(pdf_paths) > 1:
            # Use parallel processing with a thread pool
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Create a list of (pdf_path, doc_type) tuples
                tasks = [(path, dtype) for path, dtype in zip(pdf_paths, doc_types)]
                
                # Define a wrapper function to unpack the tuple and call process_document
                def process_doc(args):
                    path, dtype = args
                    try:
                        return self.process_document(path, dtype)
                    except Exception as e:
                        logger.error(f"Error processing document {path}: {str(e)}")
                        return path, {"error": str(e), "traceback": traceback.format_exc()}
                
                # Execute tasks and collect results
                results = list(executor.map(process_doc, tasks))
            
            return results
        else:
            # Process sequentially
            results = []
            for pdf_path, doc_type in zip(pdf_paths, doc_types):
                try:
                    result = self.process_document(pdf_path, doc_type)
                    results.append(result)
                except Exception as e:
                    logger.error(f"Error processing document {pdf_path}: {str(e)}")
                    results.append((pdf_path, {"error": str(e), "traceback": traceback.format_exc()}))
            
            return results
    
    def extract_profile(self, processed_document: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract a profile from the processed document data.
        
        Args:
            processed_document: Processed document data
            
        Returns:
            Profile data
        """
        # Get metadata
        metadata = processed_document.get("metadata", {})
        
        # Get linguistic features
        linguistic_features = processed_document.get("linguistic_features", {})
        
        # Get argumentation metrics
        argumentation = processed_document.get("argumentation", {})
        argumentation_metrics = argumentation.get("metrics", {})
        
        # Build profile
        profile = {
            "metadata": {
                "document_type": metadata.get("document_type", "unknown"),
                "committee": metadata.get("committee", None),
                "country": metadata.get("country", None),
                "topic": metadata.get("main_topic", None),
                "topics_discussed": metadata.get("discussed_topics", [])
            },
            "writing_style": {
                "readability": {
                    "flesch_reading_ease": linguistic_features.get("flesch_reading_ease", 0),
                    "flesch_kincaid_grade": linguistic_features.get("flesch_kincaid_grade", 0)
                },
                "complexity": {
                    "lexical_diversity": linguistic_features.get("type_token_ratio", 0),
                    "unique_word_ratio": (linguistic_features.get("unique_word_count", 0) / 
                                         max(1, linguistic_features.get("word_count", 1))),
                    "avg_word_length": linguistic_features.get("avg_word_length", 0),
                    "avg_sentence_length": linguistic_features.get("avg_sentence_length", 0)
                },
                "style_markers": {
                    "passive_voice_ratio": linguistic_features.get("passive_voice_ratio", 0),
                    "question_ratio": linguistic_features.get("question_ratio", 0),
                    "exclamation_ratio": linguistic_features.get("exclamation_ratio", 0)
                }
            },
            "argumentation": {
                "component_distribution": argumentation_metrics.get("component_percentages", {}),
                "argument_density": argumentation_metrics.get("argument_density", 0),
                "premise_to_claim_ratio": argumentation_metrics.get("premise_to_claim_ratio", 0),
                "support_to_attack_ratio": argumentation_metrics.get("support_to_attack_ratio", 0),
                "reasoning_patterns": argumentation_metrics.get("reasoning_counts", {}),
                "reasoning_diversity": argumentation_metrics.get("reasoning_diversity", 0)
            }
        }
        
        # Get POS information if available
        if "grouped_pos" in linguistic_features:
            profile["writing_style"]["pos_distribution"] = linguistic_features["grouped_pos"]
        
        # Get sentiment if available
        if "sentiment_polarity" in linguistic_features:
            profile["writing_style"]["sentiment"] = {
                "polarity": linguistic_features.get("sentiment_polarity", 0),
                "positive_word_ratio": linguistic_features.get("positive_word_ratio", 0),
                "negative_word_ratio": linguistic_features.get("negative_word_ratio", 0)
            }
        
        return profile
    
    def aggregate_profiles(self, profiles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Aggregate multiple profiles into a single profile.
        
        Args:
            profiles: List of profiles
            
        Returns:
            Aggregated profile
        """
        if not profiles:
            return {}
        
        # Initialize aggregate profile
        aggregate = {
            "metadata": {
                "document_count": len(profiles),
                "document_types": {},
                "committees": {},
                "country": None,  # Should be the same across documents
                "topics": []
            },
            "writing_style": {
                "readability": {
                    "flesch_reading_ease": 0,
                    "flesch_kincaid_grade": 0
                },
                "complexity": {
                    "lexical_diversity": 0,
                    "unique_word_ratio": 0,
                    "avg_word_length": 0,
                    "avg_sentence_length": 0
                },
                "style_markers": {
                    "passive_voice_ratio": 0,
                    "question_ratio": 0,
                    "exclamation_ratio": 0
                }
            },
            "argumentation": {
                "component_distribution": {},
                "argument_density": 0,
                "premise_to_claim_ratio": 0,
                "support_to_attack_ratio": 0,
                "reasoning_patterns": {},
                "reasoning_diversity": 0
            }
        }
        
        # Collect all topics
        all_topics = []
        
        # Aggregate profiles
        for profile in profiles:
            # Update document type counts
            doc_type = profile["metadata"].get("document_type", "unknown")
            aggregate["metadata"]["document_types"][doc_type] = (
                aggregate["metadata"]["document_types"].get(doc_type, 0) + 1
            )
            
            # Update committee counts
            committee = profile["metadata"].get("committee")
            if committee:
                aggregate["metadata"]["committees"][committee] = (
                    aggregate["metadata"]["committees"].get(committee, 0) + 1
                )
            
            # Set country (should be the same across documents)
            if profile["metadata"].get("country") and not aggregate["metadata"]["country"]:
                aggregate["metadata"]["country"] = profile["metadata"]["country"]
            
            # Collect topics
            if profile["metadata"].get("topic"):
                all_topics.append(profile["metadata"]["topic"])
            if profile["metadata"].get("topics_discussed"):
                all_topics.extend(profile["metadata"]["topics_discussed"])
            
            # Sum numeric metrics
            aggregate["writing_style"]["readability"]["flesch_reading_ease"] += (
                profile["writing_style"]["readability"].get("flesch_reading_ease", 0)
            )
            aggregate["writing_style"]["readability"]["flesch_kincaid_grade"] += (
                profile["writing_style"]["readability"].get("flesch_kincaid_grade", 0)
            )
            
            aggregate["writing_style"]["complexity"]["lexical_diversity"] += (
                profile["writing_style"]["complexity"].get("lexical_diversity", 0)
            )
            aggregate["writing_style"]["complexity"]["unique_word_ratio"] += (
                profile["writing_style"]["complexity"].get("unique_word_ratio", 0)
            )
            aggregate["writing_style"]["complexity"]["avg_word_length"] += (
                profile["writing_style"]["complexity"].get("avg_word_length", 0)
            )
            aggregate["writing_style"]["complexity"]["avg_sentence_length"] += (
                profile["writing_style"]["complexity"].get("avg_sentence_length", 0)
            )
            
            aggregate["writing_style"]["style_markers"]["passive_voice_ratio"] += (
                profile["writing_style"]["style_markers"].get("passive_voice_ratio", 0)
            )
            aggregate["writing_style"]["style_markers"]["question_ratio"] += (
                profile["writing_style"]["style_markers"].get("question_ratio", 0)
            )
            aggregate["writing_style"]["style_markers"]["exclamation_ratio"] += (
                profile["writing_style"]["style_markers"].get("exclamation_ratio", 0)
            )
            
            aggregate["argumentation"]["argument_density"] += (
                profile["argumentation"].get("argument_density", 0)
            )
            aggregate["argumentation"]["premise_to_claim_ratio"] += (
                profile["argumentation"].get("premise_to_claim_ratio", 0)
            )
            aggregate["argumentation"]["support_to_attack_ratio"] += (
                profile["argumentation"].get("support_to_attack_ratio", 0)
            )
            aggregate["argumentation"]["reasoning_diversity"] += (
                profile["argumentation"].get("reasoning_diversity", 0)
            )
            
            # Aggregate component distribution
            for comp_type, value in profile["argumentation"].get("component_distribution", {}).items():
                if comp_type not in aggregate["argumentation"]["component_distribution"]:
                    aggregate["argumentation"]["component_distribution"][comp_type] = 0
                aggregate["argumentation"]["component_distribution"][comp_type] += value
            
            # Aggregate reasoning patterns
            for reason_type, count in profile["argumentation"].get("reasoning_patterns", {}).items():
                if reason_type not in aggregate["argumentation"]["reasoning_patterns"]:
                    aggregate["argumentation"]["reasoning_patterns"][reason_type] = 0
                aggregate["argumentation"]["reasoning_patterns"][reason_type] += count
        
        # Calculate averages
        n = len(profiles)
        aggregate["writing_style"]["readability"]["flesch_reading_ease"] /= n
        aggregate["writing_style"]["readability"]["flesch_kincaid_grade"] /= n
        
        aggregate["writing_style"]["complexity"]["lexical_diversity"] /= n
        aggregate["writing_style"]["complexity"]["unique_word_ratio"] /= n
        aggregate["writing_style"]["complexity"]["avg_word_length"] /= n
        aggregate["writing_style"]["complexity"]["avg_sentence_length"] /= n
        
        aggregate["writing_style"]["style_markers"]["passive_voice_ratio"] /= n
        aggregate["writing_style"]["style_markers"]["question_ratio"] /= n
        aggregate["writing_style"]["style_markers"]["exclamation_ratio"] /= n
        
        aggregate["argumentation"]["argument_density"] /= n
        aggregate["argumentation"]["premise_to_claim_ratio"] /= n
        aggregate["argumentation"]["support_to_attack_ratio"] /= n
        aggregate["argumentation"]["reasoning_diversity"] /= n
        
        # Average component distributions
        for comp_type in aggregate["argumentation"]["component_distribution"]:
            aggregate["argumentation"]["component_distribution"][comp_type] /= n
        
        # Process topics
        if all_topics:
            # Count topic frequencies
            topic_counts = {}
            for topic in all_topics:
                topic_counts[topic] = topic_counts.get(topic, 0) + 1
            
            # Sort by frequency
            sorted_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)
            aggregate["metadata"]["topics"] = [topic for topic, count in sorted_topics]
        
        return aggregate
    
    def save_profile(self, profile: Dict[str, Any], output_path: Optional[str] = None) -> str:
        """
        Save a profile to a file or S3.
        
        Args:
            profile: Profile data
            output_path: Path to save to (if None, use default)
            
        Returns:
            Path where profile was saved
        """
        # Generate default output path if not provided
        if not output_path:
            filename = f"delegate_profile_{int(time.time())}.json"
            if self.use_s3:
                output_path = os.path.join(S3_CONFIG["output_prefix"], "profiles", filename)
            else:
                output_path = os.path.join(self.output_dir, "profiles", filename)
        
        # Create local path for saving
        local_path = output_path
        if self.use_s3 and (output_path.startswith('s3://') or not os.path.isabs(output_path)):
            # Create a temporary file
            local_path = os.path.join(self.temp_dir, f"profile_{uuid.uuid4().hex}.json")
        
        # Ensure directory exists for local path
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        
        # Save locally
        with open(local_path, 'w', encoding='utf-8') as f:
            json.dump(profile, f, indent=2, ensure_ascii=False)
        
        # Upload to S3 if needed
        if self.use_s3 and local_path != output_path:
            if output_path.startswith('s3://'):
                # Extract bucket and key from s3:// URL
                parts = output_path[5:].split('/', 1)
                if len(parts) == 1:
                    bucket, key = parts[0], filename
                else:
                    bucket, key = parts
            else:
                bucket, key = self.s3_bucket, output_path
            
            # Upload to S3
            s3 = boto3.client('s3')
            s3.upload_file(local_path, bucket, key)
            
            # Clean up temporary file
            os.remove(local_path)
            
            return f"s3://{bucket}/{key}"
        
        return local_path


# Lambda handler for AWS Lambda execution
def lambda_handler(event, context):
    """
    AWS Lambda handler for document processing.
    
    Args:
        event: Lambda event object, should contain:
            - s3_bucket: S3 bucket name (optional if in environment)
            - s3_key: S3 key of PDF to process
            - document_type: Type of document (optional)
            - processing_options: Dict of processing options (optional)
        context: Lambda context object
        
    Returns:
        Dict with processing results
    """
    # Configure logging for Lambda
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    try:
        logger.info(f"Processing Lambda event: {json.dumps(event)}")
        
        # Get parameters from event
        s3_bucket = event.get('s3_bucket', ENV_S3_BUCKET)
        s3_key = event.get('s3_key')
        document_type = event.get('document_type')
        processing_options = event.get('processing_options', {})
        
        # Validate parameters
        if not s3_bucket:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Missing S3 bucket. Provide s3_bucket in event or set PDF_TRANSFORM_S3_BUCKET environment variable.'
                })
            }
        
        if not s3_key:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Missing S3 key. Provide s3_key in event.'
                })
            }
        
        # Check if this is an SQS event
        if 'Records' in event and event.get('EventSource') == 'aws:sqs':
            logger.info("Processing SQS event")
            results = []
            
            for record in event['Records']:
                try:
                    message_body = json.loads(record['body'])
                    pdf_path = message_body.get('pdf_path')
                    doc_type = message_body.get('document_type')
                    
                    if pdf_path:
                        # Initialize pipeline with options
                        pipeline = DocumentProcessingPipeline(
                            s3_bucket=s3_bucket,
                            **processing_options
                        )
                        
                        # Process document
                        output_path, document_data = pipeline.process_document(pdf_path, doc_type)
                        
                        results.append({
                            'pdf_path': pdf_path,
                            'output_path': output_path,
                            'document_type': doc_type,
                            'status': 'processed'
                        })
                except Exception as e:
                    logger.error(f"Error processing SQS message: {str(e)}")
                    logger.error(traceback.format_exc())
                    results.append({
                        'error': str(e),
                        'pdf_path': message_body.get('pdf_path') if 'message_body' in locals() else None,
                        'status': 'error'
                    })
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': f"Processed {len(results)} documents from SQS queue",
                    'results': results
                })
            }
        
        # Initialize pipeline with options
        pipeline = DocumentProcessingPipeline(
            s3_bucket=s3_bucket,
            **processing_options
        )
        
        # Process document
        pdf_path = f"s3://{s3_bucket}/{s3_key}"
        output_path, document_data = pipeline.process_document(pdf_path, document_type)
        
        # Check if processing was queued
        if document_data and document_data.get('queued'):
            return {
                'statusCode': 202,
                'body': json.dumps({
                    'message': 'Document queued for processing',
                    'queue_data': document_data
                })
            }
        
        # Return success response
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Document processed successfully',
                'output_path': output_path,
                'metadata': {
                    'document_type': document_data.get('metadata', {}).get('document_type'),
                    'page_count': document_data.get('metadata', {}).get('page_count'),
                    'processing_time': document_data.get('processing_metadata', {}).get('processing_time')
                }
            })
        }
    
    except Exception as e:
        logger.error(f"Error in Lambda handler: {str(e)}")
        logger.error(traceback.format_exc())
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'traceback': traceback.format_exc()
            })
        }


# Mock document processor for testing
class MockDocumentProcessor:
    """Mock document processor for testing"""
    
    def __init__(self):
        """Initialize mock processor"""
        self.processed_docs = []
    
    def process_pdf(self, pdf_path, document_type=None):
        """Mock PDF processing"""
        self.processed_docs.append((pdf_path, document_type))
        return {
            "content": {
                "full_text": f"Mock content for {pdf_path}",
                "sentences": ["This is a test sentence.", "Here is another one."],
                "paragraphs": ["This is a test sentence. Here is another one."]
            },
            "metadata": {
                "document_type": document_type or "unknown",
                "page_count": 5,
                "title": "Mock Document"
            }
        }


# Main function for command line usage
def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Process documents through the pipeline")
    parser.add_argument("input", nargs="+", help="PDF file(s) to process (local paths or S3 URLs)")
    parser.add_argument("--output-dir", "-o", help="Output directory for processed files")
    parser.add_argument("--document-type", "-t", help="Document type (position_paper, speech, etc.)")
    parser.add_argument("--no-markdown", action="store_true", help="Disable markdown conversion")
    parser.add_argument("--no-spacy", action="store_true", help="Disable SpaCy for entity extraction")
    parser.add_argument("--no-transformers", action="store_true", help="Disable transformer models")
    parser.add_argument("--parallel", action="store_true", help="Enable parallel processing")
    parser.add_argument("--gpu", action="store_true", help="Use GPU for processing")
    parser.add_argument("--profile", action="store_true", help="Generate and save delegate profile")
    parser.add_argument("--s3-bucket", help="S3 bucket for storage")
    parser.add_argument("--test-mode", action="store_true", help="Enable test mode with mock processing")
    parser.add_argument("--max-workers", type=int, default=PROCESSING_OPTIONS["max_workers"], help="Maximum number of worker threads")
    
    # Model options
    parser.add_argument("--bert-model", default=MODELS["bert"]["default"], help="BERT model to use")
    parser.add_argument("--component-model", default=MODELS["argument_component"]["default"], 
                       help="Model for argument component detection")
    parser.add_argument("--relation-model", default=MODELS["argument_relation"]["default"], 
                       help="Model for argument relation classification")
    parser.add_argument("--reasoning-model", default=MODELS["reasoning"]["default"], 
                       help="Model for reasoning pattern classification")
    
    args = parser.parse_args()
    
    # Check for test mode
    if args.test_mode:
        os.environ["TEST_ENV"] = "true"
        
        # Use mock processor in test mode
        global pdf_processor
        pdf_processor = MockDocumentProcessor()
    
    # Initialize pipeline
    pipeline = DocumentProcessingPipeline(
        use_markdown=not args.no_markdown,
        use_spacy=not args.no_spacy,
        use_transformers=not args.no_transformers,
        parallel_processing=args.parallel,
        bert_model=args.bert_model,
        component_model=args.component_model,
        relation_model=args.relation_model,
        reasoning_model=args.reasoning_model,
        use_gpu=args.gpu,
        output_dir=args.output_dir,
        s3_bucket=args.s3_bucket,
        max_workers=args.max_workers
    )
    
    # Process documents
    document_type = args.document_type
    document_types = [document_type] * len(args.input) if document_type else None
    results = pipeline.process_multiple_documents(args.input, document_types)
    
    # Generate profile if requested
    if args.profile:
        # Extract profiles
        profiles = [pipeline.extract_profile(doc_data) for _, doc_data in results 
                    if isinstance(doc_data, dict) and not doc_data.get('error') and not doc_data.get('queued')]
        
        # Aggregate profiles
        aggregate_profile = pipeline.aggregate_profiles(profiles)
        
        # Save aggregate profile
        profile_path = pipeline.save_profile(aggregate_profile)
        
        print(f"Delegate profile saved to {profile_path}")
    
    print(f"Processing completed for {len(results)} documents")
    
    # Print any errors
    errors = [(path, data.get('error')) for path, data in results 
              if isinstance(data, dict) and data.get('error')]
    if errors:
        print(f"\nEncountered {len(errors)} errors:")
        for path, error in errors:
            print(f"  - {path}: {error}")
    
    # Print any queued documents
    queued = [(path, data.get('message_id')) for path, data in results 
              if isinstance(data, dict) and data.get('queued')]
    if queued:
        print(f"\n{len(queued)} documents queued for batch processing:")
        for path, message_id in queued:
            print(f"  - {path}: Message ID {message_id}")


if __name__ == "__main__":
    main()
