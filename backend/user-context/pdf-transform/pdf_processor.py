#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PDF Processor Module

This module handles the extraction and processing of text from PDF documents
using PyMuPDF and PyMuPDF4LLM. It converts PDFs to structured text while
preserving formatting and extracting metadata.

AWS Lambda optimized with S3 integration and efficient resource usage.
"""

import os
import re
import json
import time
import logging
import hashlib
import tempfile
from pathlib import Path
from functools import lru_cache
from typing import Dict, List, Tuple, Optional, Any, Union, BinaryIO

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
ENV_MEMORY_LIMIT = int(os.environ.get("PDF_PROCESSOR_MEMORY_LIMIT", "0"))
ENV_MODEL_CACHE_DIR = os.environ.get("MODEL_CACHE_DIR", "/tmp/model_cache" if ENV_AWS_LAMBDA else "./model_cache")
ENV_USE_MARKDOWN = os.environ.get("USE_MARKDOWN", "true").lower() == "true" and not ENV_TEST_MODE
ENV_CLOUDWATCH_NAMESPACE = os.environ.get("CLOUDWATCH_METRICS_NAMESPACE", "PDFTransform")
ENV_S3_BUCKET = os.environ.get("PDF_TRANSFORM_S3_BUCKET")
ENV_SQS_QUEUE_URL = os.environ.get("PDF_TRANSFORM_SQS_QUEUE_URL")
ENV_SQS_LARGE_FILE_THRESHOLD = int(os.environ.get("SQS_LARGE_FILE_THRESHOLD", "10485760"))  # 10MB
ENV_MAX_PAGES = int(os.environ.get("PDF_MAX_PAGES", "0"))  # 0 = no limit

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
os.environ["NLTK_DATA"] = str(model_cache_dir / "nltk_data")

# Import PyMuPDF and NLTK after configuring cache paths
import fitz  # PyMuPDF
import nltk
nltk_data_path = Path(os.environ["NLTK_DATA"])
if not nltk_data_path.exists():
    nltk_data_path.mkdir(parents=True, exist_ok=True)

# Ensure NLTK resources are available - always download in advance
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True, download_dir=str(nltk_data_path))

from nltk.tokenize import sent_tokenize

# PyMuPDF4LLM for markdown conversion - only import if needed and available
pdf2markdown = None
if ENV_USE_MARKDOWN:
    try:
        from pymupdf4llm import PDF2Markdown
        pdf2markdown = PDF2Markdown()
        logger.info("Preloaded PyMuPDF4LLM for Lambda environment")
    except ImportError:
        logger.warning("PyMuPDF4LLM not available, markdown conversion disabled")
        ENV_USE_MARKDOWN = False
        pdf2markdown = None


class PDFProcessor:
    """Main class for processing PDF documents"""
    
    def __init__(self, 
                 use_markdown: bool = ENV_USE_MARKDOWN,
                 test_mode: bool = ENV_TEST_MODE,
                 memory_limit: int = ENV_MEMORY_LIMIT,
                 max_pages: int = ENV_MAX_PAGES):
        """
        Initialize the PDF processor.
        
        Args:
            use_markdown: Whether to attempt conversion to markdown
            test_mode: Whether to run in test mode with simplified processing
            memory_limit: Memory limit in MB (0 for no limit)
            max_pages: Maximum number of pages to process (0 for no limit)
        """
        self.use_markdown = use_markdown and not test_mode
        self.test_mode = test_mode
        self.memory_limit = memory_limit
        self.max_pages = max_pages
        
        # Track initialization time
        self.init_start_time = time.time()
        
        # Initialize AWS clients if available
        self.s3_client = None
        self.sqs_client = None
        if AWS_AVAILABLE:
            try:
                self.s3_client = boto3.client('s3')
                if ENV_SQS_QUEUE_URL:
                    self.sqs_client = boto3.client('sqs')
            except Exception as e:
                logger.warning(f"Failed to initialize AWS clients: {e}")
        
        # PyMuPDF4LLM might not be installed, so we import it conditionally
        self.markdown_converter = None
        if self.use_markdown:
            try:
                # Use global instance if already loaded
                if pdf2markdown is not None:
                    self.markdown_converter = pdf2markdown
                else:
                    from pymupdf4llm import PDF2Markdown
                    self.markdown_converter = PDF2Markdown()
                logger.info(f"PyMuPDF4LLM loaded successfully in {time.time() - self.init_start_time:.2f}s")
            except ImportError:
                logger.warning("PyMuPDF4LLM not found. Markdown conversion will be skipped.")
                self.use_markdown = False
                self.markdown_converter = None
        
        logger.info(f"PDFProcessor initialized in {time.time() - self.init_start_time:.2f}s " + 
                   f"(markdown={self.use_markdown}, test_mode={self.test_mode})")
    
    def process_pdf(self, pdf_path: str, document_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Process a PDF document and extract both text and structure.
        
        Args:
            pdf_path: Path to the PDF file
            document_type: Type of document (position_paper, speech, etc.)
            
        Returns:
            A dictionary containing the processed document data
        """
        start_time = time.time()
        
        try:
            if not os.path.exists(pdf_path):
                raise FileNotFoundError(f"PDF file not found: {pdf_path}")
            
            # Check file size - for large files, we may want to offload to SQS in Lambda
            file_size = os.path.getsize(pdf_path)
            
            if ENV_AWS_LAMBDA and self.sqs_client and file_size > ENV_SQS_LARGE_FILE_THRESHOLD:
                logger.info(f"Large PDF detected ({file_size} bytes), offloading to SQS")
                return self._queue_large_file_processing(pdf_path, document_type)
            
            # Initialize document data structure
            document_data = self._init_document_data(pdf_path, document_type)
            
            # Use simplified processing in test mode
            if self.test_mode:
                document_data = self._process_test_mode(pdf_path, document_data)
                processing_time = time.time() - start_time
                logger.info(f"Processed PDF in test mode in {processing_time:.2f}s")
                
                # Add processing metadata
                document_data["metadata"]["processing_metadata"] = {
                    "test_mode": True,
                    "processing_time": processing_time,
                    "timestamp": time.time()
                }
                
                return document_data
            
            # Extract text using PyMuPDF
            doc = fitz.open(pdf_path)
            
            # Check page limit if specified
            if self.max_pages > 0 and len(doc) > self.max_pages:
                logger.warning(f"PDF exceeds maximum page limit ({len(doc)} > {self.max_pages}), truncating")
                max_pages = self.max_pages
            else:
                max_pages = len(doc)
            
            # Extract text by pages
            pages_text = []
            for page_num in range(max_pages):
                page = doc[page_num]
                text = page.get_text()
                pages_text.append(text)
            
            # Join all pages
            full_text = "\n\n".join(pages_text)
            document_data["content"]["full_text"] = self._clean_text(full_text)
            
            # Extract page count and document info
            document_data["metadata"]["page_count"] = len(doc)
            document_data["metadata"]["processed_pages"] = max_pages
            
            if doc.metadata:
                if doc.metadata.get("title"):
                    document_data["metadata"]["title"] = doc.metadata.get("title")
                if doc.metadata.get("author"):
                    document_data["metadata"]["author"] = doc.metadata.get("author")
            
            # Convert to markdown if enabled
            if self.use_markdown and self.markdown_converter:
                try:
                    markdown_start = time.time()
                    markdown_text = self.markdown_converter.convert(pdf_path)
                    document_data["content"]["markdown"] = markdown_text
                    markdown_time = time.time() - markdown_start
                    
                    logger.info(f"Successfully converted {pdf_path} to markdown in {markdown_time:.2f}s")
                    
                    # Report markdown conversion metrics
                    if metrics and AWS_AVAILABLE:
                        try:
                            metrics['put_metric']('MarkdownConversionTime', markdown_time, 'Seconds')
                        except Exception:
                            pass
                except Exception as e:
                    logger.error(f"Markdown conversion failed: {e}")
                    document_data["content"]["markdown"] = ""
            
            # Process document structure
            document_data = self._process_structure(document_data)
            
            # Close the document
            doc.close()
            
            # Add processing metadata
            processing_time = time.time() - start_time
            document_data["metadata"]["processing_metadata"] = {
                "test_mode": False,
                "processing_time": processing_time,
                "file_size_bytes": file_size,
                "memory_limited": self.memory_limit > 0,
                "markdown_used": self.use_markdown,
                "timestamp": time.time()
            }
            
            # Report metrics if available
            if metrics and AWS_AVAILABLE:
                try:
                    metrics['put_metric']('PDFProcessingTime', processing_time, 'Seconds')
                    metrics['put_metric']('PDFFileSize', file_size, 'Bytes')
                    metrics['put_metric']('PDFPages', document_data["metadata"]["page_count"], 'Count')
                except Exception as e:
                    logger.warning(f"Failed to report metrics: {e}")
            
            logger.info(f"Processed PDF in {processing_time:.2f}s")
            return document_data
            
        except Exception as e:
            logger.error(f"Error processing PDF: {e}")
            
            # Create basic error document data
            if 'document_data' not in locals():
                document_data = self._init_document_data(pdf_path, document_type)
            
            # Add error info to metadata
            if "processing_metadata" not in document_data["metadata"]:
                document_data["metadata"]["processing_metadata"] = {}
            
            document_data["metadata"]["processing_metadata"].update({
                "error": str(e),
                "processing_time": time.time() - start_time,
                "timestamp": time.time()
            })
            
            # Report error metric
            if metrics and AWS_AVAILABLE:
                try:
                    metrics['put_metric']('PDFProcessingErrors', 1, 'Count')
                except Exception:
                    pass
            
            return document_data
    
    def process_pdf_from_s3(self, bucket: str, key: str, document_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Process a PDF document from S3 and extract both text and structure.
        
        Args:
            bucket: S3 bucket name
            key: S3 object key
            document_type: Type of document (position_paper, speech, etc.)
            
        Returns:
            A dictionary containing the processed document data
        """
        if not AWS_AVAILABLE or not self.s3_client:
            raise ImportError("boto3 is required for S3 operations")
        
        try:
            # First, check if the file exists and get its size
            head_response = self.s3_client.head_object(Bucket=bucket, Key=key)
            file_size = head_response['ContentLength']
            
            # For large files, we might want to offload to SQS in Lambda
            if ENV_AWS_LAMBDA and self.sqs_client and file_size > ENV_SQS_LARGE_FILE_THRESHOLD:
                logger.info(f"Large PDF detected in S3 ({file_size} bytes), offloading to SQS")
                return self._queue_large_file_processing_s3(bucket, key, document_type)
            
            # Create a temporary file
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
                temp_path = temp_file.name
                
                # Download the file from S3
                logger.info(f"Downloading PDF from s3://{bucket}/{key} to {temp_path}")
                self.s3_client.download_file(bucket, key, temp_path)
                
                # Process the PDF
                result = self.process_pdf(temp_path, document_type)
                
                # Add S3 metadata
                if "processing_metadata" not in result["metadata"]:
                    result["metadata"]["processing_metadata"] = {}
                
                result["metadata"]["processing_metadata"]["s3_source"] = {
                    "bucket": bucket,
                    "key": key,
                    "size": file_size,
                    "last_modified": head_response.get('LastModified', '').isoformat() if head_response.get('LastModified') else None
                }
                
                # Update the file path to show original S3 location
                result["metadata"]["file_path"] = f"s3://{bucket}/{key}"
                
                # Clean up the temporary file
                try:
                    os.unlink(temp_path)
                except Exception as e:
                    logger.warning(f"Failed to delete temporary file {temp_path}: {e}")
                
                return result
                
        except ClientError as e:
            logger.error(f"Error processing PDF from S3: {e}")
            
            # Create basic error document data
            document_data = self._init_document_data(f"s3://{bucket}/{key}", document_type)
            
            # Add error info to metadata
            document_data["metadata"]["processing_metadata"] = {
                "error": str(e),
                "s3_source": {
                    "bucket": bucket,
                    "key": key
                },
                "timestamp": time.time()
            }
            
            return document_data
    
    def process_pdf_bytes(self, pdf_bytes: bytes, filename: str, document_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Process a PDF document from memory bytes.
        
        Args:
            pdf_bytes: PDF file contents as bytes
            filename: A name to use for the PDF (for reference only)
            document_type: Type of document (position_paper, speech, etc.)
            
        Returns:
            A dictionary containing the processed document data
        """
        start_time = time.time()
        
        try:
            # Check size - for large files, we may want to offload to SQS in Lambda
            file_size = len(pdf_bytes)
            
            if ENV_AWS_LAMBDA and self.sqs_client and file_size > ENV_SQS_LARGE_FILE_THRESHOLD:
                logger.info(f"Large PDF bytes detected ({file_size} bytes), offloading to SQS")
                return self._queue_large_file_processing_bytes(pdf_bytes, filename, document_type)
            
            # Create a temporary file
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
                temp_path = temp_file.name
                temp_file.write(pdf_bytes)
                
            # Process the temporary file
            result = self.process_pdf(temp_path, document_type)
            
            # Update the file path and name
            result["metadata"]["file_name"] = filename
            result["metadata"]["file_path"] = "[memory]"
            
            # Add byte processing metadata
            if "processing_metadata" not in result["metadata"]:
                result["metadata"]["processing_metadata"] = {}
            
            result["metadata"]["processing_metadata"]["memory_source"] = {
                "file_size": file_size,
                "filename": filename
            }
            
            # Clean up the temporary file
            try:
                os.unlink(temp_path)
            except Exception as e:
                logger.warning(f"Failed to delete temporary file {temp_path}: {e}")
            
            logger.info(f"Processed PDF bytes in {time.time() - start_time:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"Error processing PDF bytes: {e}")
            
            # Create basic error document data
            document_data = self._init_document_data(f"[memory]:{filename}", document_type)
            
            # Add error info to metadata
            document_data["metadata"]["processing_metadata"] = {
                "error": str(e),
                "memory_source": {
                    "file_size": len(pdf_bytes),
                    "filename": filename
                },
                "processing_time": time.time() - start_time,
                "timestamp": time.time()
            }
            
            return document_data

    def _init_document_data(self, pdf_path: str, document_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Initialize the document data structure.
        
        Args:
            pdf_path: Path to the PDF file
            document_type: Type of document
            
        Returns:
            Initialized document data dictionary
        """
        # Detect document type if not provided
        if not document_type:
            document_type = self._detect_document_type(pdf_path)
        
        document_data = {
            "metadata": {
                "file_name": os.path.basename(pdf_path),
                "file_path": pdf_path,
                "document_type": document_type,
                "committee": None,
                "country": None,
                "main_topic": None,
                "discussed_topics": [],
                "date": None,
                "page_count": 0,
                "processed_pages": 0,
                "title": None,
                "author": None
            },
            "content": {
                "full_text": "",
                "markdown": "",
                "sections": [],
                "paragraphs": [],
                "sentences": []
            },
            "bert_friendly": {
                "segments": [],
                "token_count": 0,
                "segment_count": 0,
                "marked_text": ""
            },
            "features": {
                "readability": {},
                "complexity": {},
                "document_stats": {}
            }
        }
        
        return document_data
    
    def _detect_document_type(self, pdf_path: str) -> str:
        """
        Attempt to detect the document type based on the file name.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Detected document type or 'unknown'
        """
        filename = os.path.basename(pdf_path).lower()
        
        if any(term in filename for term in ["position", "paper", "position_paper"]):
            return "position_paper"
        elif any(term in filename for term in ["speech", "address", "statement"]):
            return "speech"
        else:
            return "unknown"
    
    def _clean_text(self, text: str) -> str:
        """
        Clean the extracted text.
        
        Args:
            text: Text to clean
            
        Returns:
            Cleaned text
        """
        # Replace multiple spaces
        text = re.sub(r'\s+', ' ', text)
        
        # Fix line breaks (preserve paragraph breaks)
        text = re.sub(r'(?<!\n)\n(?!\n)', ' ', text)
        
        # Remove control characters
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\xff]', '', text)
        
        # Normalize whitespace around punctuation
        text = re.sub(r'\s*([.,;:!?])\s*', r'\1 ', text)
        
        # Double newlines for paragraph breaks
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text.strip()
    
    def _process_structure(self, document_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process the document structure.
        
        Args:
            document_data: Document data dictionary
            
        Returns:
            Document data with structure processed
        """
        text = document_data["content"]["full_text"]
        
        # Extract paragraphs (text blocks separated by double line breaks)
        paragraphs = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]
        document_data["content"]["paragraphs"] = paragraphs
        
        # Extract sentences
        sentences = []
        for para in paragraphs:
            try:
                sent_list = sent_tokenize(para)
                sentences.extend(sent_list)
            except Exception as e:
                logger.warning(f"Error tokenizing sentences: {e}")
                # Fallback: simple period-based splitting
                simple_sents = [s.strip() + '.' for s in para.split('.') if s.strip()]
                sentences.extend(simple_sents)
        
        document_data["content"]["sentences"] = sentences
        
        # Attempt to identify sections based on formatting patterns
        sections = self._extract_sections(text, paragraphs)
        document_data["content"]["sections"] = sections
        
        # Update document stats
        document_data["features"]["document_stats"] = {
            "paragraph_count": len(paragraphs),
            "sentence_count": len(sentences),
            "word_count": len(text.split()),
            "character_count": len(text)
        }
        
        return document_data
    
    def _extract_sections(self, text: str, paragraphs: List[str]) -> List[Dict[str, Any]]:
        """
        Extract sections from the document.
        
        Args:
            text: Full document text
            paragraphs: List of paragraphs
            
        Returns:
            List of detected sections
        """
        sections = []
        
        # Look for common section headers
        section_patterns = [
            # Format: header pattern, section type
            (r'(?i)^\s*introduction\s*$', 'introduction'),
            (r'(?i)^\s*background\s*$', 'background'),
            (r'(?i)^\s*conclusion\s*$', 'conclusion'),
            (r'(?i)^\s*recommendations?\s*$', 'recommendations'),
            (r'(?i)^\s*analysis\s*$', 'analysis'),
            (r'(?i)^\s*position\s*$', 'position'),
            (r'(?i)^\s*arguments?\s*$', 'arguments'),
            # Numbered or lettered sections
            (r'^\s*[IVX]+\.\s+(.+)$', 'numbered'),  # Roman numerals
            (r'^\s*[0-9]+\.\s+(.+)$', 'numbered'),  # Arabic numerals
            (r'^\s*[A-Z]\.\s+(.+)$', 'lettered')    # Lettered sections
        ]
        
        current_section = None
        section_content = []
        
        for para in paragraphs:
            is_header = False
            
            # Check if paragraph is a section header
            for pattern, section_type in section_patterns:
                match = re.match(pattern, para, re.MULTILINE)
                if match:
                    # If we have a current section, save it before starting new one
                    if current_section and section_content:
                        sections.append({
                            "title": current_section,
                            "type": section_type,
                            "content": "\n\n".join(section_content)
                        })
                        section_content = []
                    
                    # Extract the section title from the match or use the paragraph
                    if len(match.groups()) > 0:
                        current_section = match.group(1)
                    else:
                        current_section = para
                    
                    is_header = True
                    break
            
            # If not a header, add to current section content
            if not is_header:
                section_content.append(para)
        
        # Add the last section
        if current_section and section_content:
            sections.append({
                "title": current_section,
                "type": "unknown",
                "content": "\n\n".join(section_content)
            })
        
        # If no sections were found, create a default one
        if not sections and paragraphs:
            sections.append({
                "title": "Main Content",
                "type": "default",
                "content": text
            })
        
        return sections

    def save_to_json(self, document_data: Dict[str, Any], output_path: Optional[str] = None) -> str:
        """
        Save the processed document data to a JSON file.
        
        Args:
            document_data: Document data dictionary
            output_path: Path to save JSON file (if None, derives from input file)
            
        Returns:
            Path to the saved JSON file
        """
        if not output_path:
            input_path = document_data["metadata"]["file_path"]
            # Handle S3 paths or memory paths
            if input_path.startswith("s3://") or input_path.startswith("[memory]"):
                if document_data["metadata"]["file_name"]:
                    base_name = os.path.splitext(document_data["metadata"]["file_name"])[0]
                    output_path = f"{base_name}_processed.json"
                else:
                    output_path = "document_processed.json"
            else:
                output_path = os.path.splitext(input_path)[0] + "_processed.json"
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(document_data, f, indent=2, ensure_ascii=False)
            
        logger.info(f"Saved processed document to {output_path}")
        return output_path
    
    def _hash_file(self, file_path: str) -> str:
        """
        Calculate MD5 hash of a file.
        
        Args:
            file_path: Path to file
            
        Returns:
            MD5 hash as hex string
        """
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def save_to_s3(self, document_data: Dict[str, Any], bucket: str, key: str) -> str:
        """
        Save processed document data to S3.
        
        Args:
            document_data: Document data dictionary
            bucket: S3 bucket name
            key: S3 object key
            
        Returns:
            S3 URI of saved object
        """
        if not AWS_AVAILABLE or not self.s3_client:
            raise ImportError("boto3 is required for S3 operations")
        
        try:
            # Convert to JSON
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
    
    def _queue_large_file_processing(self, pdf_path: str, document_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Queue a large PDF file for asynchronous processing via SQS.
        
        Args:
            pdf_path: Path to the PDF file
            document_type: Type of document
            
        Returns:
            Initial document data with queue information
        """
        if not self.sqs_client or not ENV_SQS_QUEUE_URL:
            raise ValueError("SQS client or queue URL not available")
        
        try:
            # Get file information
            file_size = os.path.getsize(pdf_path)
            file_hash = self._hash_file(pdf_path)
            
            # Initialize document data
            document_data = self._init_document_data(pdf_path, document_type)
            
            # Upload the PDF to S3 if we have S3 access
            s3_location = None
            if self.s3_client and ENV_S3_BUCKET:
                s3_key = f"uploads/{file_hash}/{os.path.basename(pdf_path)}"
                try:
                    self.s3_client.upload_file(pdf_path, ENV_S3_BUCKET, s3_key)
                    s3_location = f"s3://{ENV_S3_BUCKET}/{s3_key}"
                    logger.info(f"Uploaded large PDF to {s3_location}")
                except Exception as e:
                    logger.error(f"Failed to upload PDF to S3: {e}")
            
            # Create SQS message
            message = {
                "task": "process_pdf",
                "file_path": pdf_path,
                "file_size": file_size,
                "file_hash": file_hash,
                "document_type": document_type,
                "timestamp": time.time()
            }
            
            if s3_location:
                message["s3_location"] = s3_location
            
            # Send message to SQS
            response = self.sqs_client.send_message(
                QueueUrl=ENV_SQS_QUEUE_URL,
                MessageBody=json.dumps(message),
                MessageAttributes={
                    'TaskType': {
                        'DataType': 'String',
                        'StringValue': 'process_pdf'
                    },
                    'FileSize': {
                        'DataType': 'Number',
                        'StringValue': str(file_size)
                    }
                }
            )
            
            # Add queue metadata to document data
            document_data["metadata"]["queued"] = True
            document_data["metadata"]["processing_metadata"] = {
                "queued": True,
                "queue_message_id": response.get('MessageId'),
                "file_size": file_size,
                "file_hash": file_hash,
                "s3_location": s3_location,
                "queue_url": ENV_SQS_QUEUE_URL,
                "timestamp": time.time()
            }
            
            # Report SQS metrics
            if metrics:
                try:
                    metrics['put_metric']('FileQueuedForProcessing', 1, 'Count')
                    metrics['put_metric']('QueuedFileSize', file_size, 'Bytes')
                except Exception:
                    pass
            
            logger.info(f"Queued large PDF ({file_size} bytes) with message ID: {response.get('MessageId')}")
            return document_data
            
        except Exception as e:
            logger.error(f"Error queueing large file: {e}")
            
            # Return basic document data with error
            document_data = self._init_document_data(pdf_path, document_type)
            document_data["metadata"]["processing_metadata"] = {
                "error": f"Failed to queue large file: {str(e)}",
                "timestamp": time.time()
            }
            return document_data
    
    def _queue_large_file_processing_s3(self, bucket: str, key: str, document_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Queue a large PDF file from S3 for asynchronous processing via SQS.
        
        Args:
            bucket: S3 bucket name
            key: S3 object key
            document_type: Type of document
            
        Returns:
            Initial document data with queue information
        """
        if not self.sqs_client or not ENV_SQS_QUEUE_URL:
            raise ValueError("SQS client or queue URL not available")
        
        try:
            # Get file information
            head_response = self.s3_client.head_object(Bucket=bucket, Key=key)
            file_size = head_response['ContentLength']
            
            # Initialize document data
            document_data = self._init_document_data(f"s3://{bucket}/{key}", document_type)
            
            # Create SQS message
            message = {
                "task": "process_pdf_s3",
                "s3_bucket": bucket,
                "s3_key": key,
                "file_size": file_size,
                "document_type": document_type,
                "timestamp": time.time()
            }
            
            # Send message to SQS
            response = self.sqs_client.send_message(
                QueueUrl=ENV_SQS_QUEUE_URL,
                MessageBody=json.dumps(message),
                MessageAttributes={
                    'TaskType': {
                        'DataType': 'String',
                        'StringValue': 'process_pdf_s3'
                    },
                    'FileSize': {
                        'DataType': 'Number',
                        'StringValue': str(file_size)
                    }
                }
            )
            
            # Add queue metadata to document data
            document_data["metadata"]["queued"] = True
            document_data["metadata"]["processing_metadata"] = {
                "queued": True,
                "queue_message_id": response.get('MessageId'),
                "file_size": file_size,
                "s3_location": f"s3://{bucket}/{key}",
                "queue_url": ENV_SQS_QUEUE_URL,
                "timestamp": time.time()
            }
            
            # Report SQS metrics
            if metrics:
                try:
                    metrics['put_metric']('S3FileQueuedForProcessing', 1, 'Count')
                    metrics['put_metric']('QueuedS3FileSize', file_size, 'Bytes')
                except Exception:
                    pass
            
            logger.info(f"Queued large S3 PDF ({file_size} bytes) with message ID: {response.get('MessageId')}")
            return document_data
            
        except Exception as e:
            logger.error(f"Error queueing large S3 file: {e}")
            
            # Return basic document data with error
            document_data = self._init_document_data(f"s3://{bucket}/{key}", document_type)
            document_data["metadata"]["processing_metadata"] = {
                "error": f"Failed to queue large S3 file: {str(e)}",
                "timestamp": time.time()
            }
            return document_data
    
    def _queue_large_file_processing_bytes(self, pdf_bytes: bytes, filename: str, document_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Queue a large PDF bytes object for asynchronous processing via SQS.
        
        Args:
            pdf_bytes: PDF file contents as bytes
            filename: A name to use for the PDF
            document_type: Type of document
            
        Returns:
            Initial document data with queue information
        """
        if not self.sqs_client or not ENV_SQS_QUEUE_URL:
            raise ValueError("SQS client or queue URL not available")
        
        try:
            # Get file information
            file_size = len(pdf_bytes)
            file_hash = hashlib.md5(pdf_bytes).hexdigest()
            
            # Initialize document data
            document_data = self._init_document_data(f"[memory]:{filename}", document_type)
            
            # Upload the PDF to S3 if we have S3 access
            s3_location = None
            if self.s3_client and ENV_S3_BUCKET:
                s3_key = f"uploads/{file_hash}/{filename}"
                try:
                    self.s3_client.put_object(
                        Bucket=ENV_S3_BUCKET,
                        Key=s3_key,
                        Body=pdf_bytes,
                        ContentType='application/pdf'
                    )
                    s3_location = f"s3://{ENV_S3_BUCKET}/{s3_key}"
                    logger.info(f"Uploaded large PDF bytes to {s3_location}")
                except Exception as e:
                    logger.error(f"Failed to upload PDF bytes to S3: {e}")
            
            # Create SQS message
            message = {
                "task": "process_pdf_s3" if s3_location else "process_pdf_bytes",
                "file_size": file_size,
                "file_hash": file_hash,
                "filename": filename,
                "document_type": document_type,
                "timestamp": time.time()
            }
            
            if s3_location:
                message["s3_bucket"] = ENV_S3_BUCKET
                message["s3_key"] = s3_key
            
            # Send message to SQS
            response = self.sqs_client.send_message(
                QueueUrl=ENV_SQS_QUEUE_URL,
                MessageBody=json.dumps(message),
                MessageAttributes={
                    'TaskType': {
                        'DataType': 'String',
                        'StringValue': 'process_pdf_bytes'
                    },
                    'FileSize': {
                        'DataType': 'Number',
                        'StringValue': str(file_size)
                    }
                }
            )
            
            # Add queue metadata to document data
            document_data["metadata"]["queued"] = True
            document_data["metadata"]["processing_metadata"] = {
                "queued": True,
                "queue_message_id": response.get('MessageId'),
                "file_size": file_size,
                "file_hash": file_hash,
                "filename": filename,
                "s3_location": s3_location,
                "queue_url": ENV_SQS_QUEUE_URL,
                "timestamp": time.time()
            }
            
            # Report SQS metrics
            if metrics:
                try:
                    metrics['put_metric']('BytesQueuedForProcessing', 1, 'Count')
                    metrics['put_metric']('QueuedBytesSize', file_size, 'Bytes')
                except Exception:
                    pass
            
            logger.info(f"Queued large PDF bytes ({file_size} bytes) with message ID: {response.get('MessageId')}")
            return document_data
            
        except Exception as e:
            logger.error(f"Error queueing large bytes: {e}")
            
            # Return basic document data with error
            document_data = self._init_document_data(f"[memory]:{filename}", document_type)
            document_data["metadata"]["processing_metadata"] = {
                "error": f"Failed to queue large bytes: {str(e)}",
                "timestamp": time.time()
            }
            return document_data
    
    def _process_test_mode(self, pdf_path: str, document_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a PDF in test mode with simplified extraction.
        
        Args:
            pdf_path: Path to the PDF file
            document_data: Initial document data
            
        Returns:
            Document data with basic test extraction
        """
        try:
            # Open the PDF with minimal extraction
            doc = fitz.open(pdf_path)
            
            # Just extract the first page for test mode
            if len(doc) > 0:
                text = doc[0].get_text()
                document_data["content"]["full_text"] = self._clean_text(text)
                
                # Extract a few sentences for testing
                sentences = sent_tokenize(document_data["content"]["full_text"])
                document_data["content"]["sentences"] = sentences[:10]  # First 10 sentences only
                
                # Extract paragraphs (simple approach)
                paragraphs = [p.strip() for p in document_data["content"]["full_text"].split("\n\n") if p.strip()]
                document_data["content"]["paragraphs"] = paragraphs[:5]  # First 5 paragraphs only
            
            # Basic metadata
            document_data["metadata"]["page_count"] = len(doc)
            document_data["metadata"]["processed_pages"] = 1
            
            # Add document info
            if doc.metadata:
                if doc.metadata.get("title"):
                    document_data["metadata"]["title"] = doc.metadata.get("title")
                if doc.metadata.get("author"):
                    document_data["metadata"]["author"] = doc.metadata.get("author")
            
            # Close the document
            doc.close()
            
            logger.info(f"Processed PDF in test mode (extracted first page from {document_data['metadata']['page_count']} pages)")
            return document_data
            
        except Exception as e:
            logger.error(f"Error in test mode processing: {e}")
            document_data["metadata"]["error"] = str(e)
            return document_data


# Create sample test data for testing purposes
def create_test_pdf(output_path: str = "test_document.pdf") -> str:
    """
    Create a sample PDF document for testing.
    
    Args:
        output_path: Path to save the test PDF
        
    Returns:
        Path to the created test PDF
    """
    try:
        # Make sure PyMuPDF is available
        import fitz
        
        # Create a new PDF document
        doc = fitz.open()
        
        # Add a page
        page = doc.new_page()
        
        # Add content to the page
        font_size = 11
        line_height = font_size * 1.2
        
        # Header
        page.insert_text((50, 50), "POSITION PAPER", fontsize=16)
        page.insert_text((50, 50 + line_height * 2), "Committee: United Nations Security Council", fontsize=font_size)
        page.insert_text((50, 50 + line_height * 3), "Topic: Nuclear Non-Proliferation in Middle East", fontsize=font_size)
        page.insert_text((50, 50 + line_height * 4), "Country: United States of America", fontsize=font_size)
        page.insert_text((50, 50 + line_height * 5), "Date: January 15, 2023", fontsize=font_size)
        
        # Introduction
        y_pos = 50 + line_height * 7
        intro_text = (
            "The United States delegation to the United Nations Security Council expresses its "
            "commitment to addressing the critical issue of nuclear non-proliferation in the Middle East. "
            "Our position remains focused on promoting a weapons-free zone while ensuring regional "
            "security and stability."
        )
        
        # Word-wrap text (simple approach)
        words = intro_text.split()
        line = ""
        for word in words:
            test_line = line + " " + word if line else word
            if len(test_line) > 80:  # Approximate line length
                page.insert_text((50, y_pos), line, fontsize=font_size)
                y_pos += line_height
                line = word
            else:
                line = test_line
        
        if line:
            page.insert_text((50, y_pos), line, fontsize=font_size)
            y_pos += line_height * 2
        
        # Body paragraphs
        paragraphs = [
            "Nuclear proliferation poses an existential threat to peace in the region. The United States "
            "supports a comprehensive approach to preventing the spread of nuclear weapons, maintaining "
            "the integrity of the Non-Proliferation Treaty, and working toward eventual disarmament.",
            
            "The United States supports the following key principles:",
            
            "1. Strengthening the Non-Proliferation Treaty framework",
            "2. Encouraging diplomatic solutions to regional tensions",
            "3. Implementing robust verification mechanisms",
            "4. Supporting peaceful nuclear energy development",
            
            "The delegation believes that international cooperation and multilateral agreements represent "
            "the best path forward for achieving lasting peace and security in the Middle East. We urge "
            "all parties to engage constructively in dialogue and confidence-building measures."
        ]
        
        for para in paragraphs:
            # Simple word wrap
            words = para.split()
            line = ""
            for word in words:
                test_line = line + " " + word if line else word
                if len(test_line) > 80:
                    page.insert_text((50, y_pos), line, fontsize=font_size)
                    y_pos += line_height
                    line = word
                else:
                    line = test_line
            
            if line:
                page.insert_text((50, y_pos), line, fontsize=font_size)
                y_pos += line_height * 2
        
        # Save the document
        doc.save(output_path)
        doc.close()
        
        return output_path
        
    except ImportError:
        # Fallback if PyMuPDF can't create PDFs
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.lib import colors
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            
            # Set up styles
            styles = getSampleStyleSheet()
            title_style = styles['Title']
            heading_style = styles['Heading2']
            normal_style = styles['Normal']
            
            # Create PDF document
            doc = SimpleDocTemplate(output_path, pagesize=letter)
            
            # Content
            content = []
            
            # Header
            content.append(Paragraph("POSITION PAPER", title_style))
            content.append(Spacer(1, 12))
            content.append(Paragraph("Committee: United Nations Security Council", normal_style))
            content.append(Paragraph("Topic: Nuclear Non-Proliferation in Middle East", normal_style))
            content.append(Paragraph("Country: United States of America", normal_style))
            content.append(Paragraph("Date: January 15, 2023", normal_style))
            content.append(Spacer(1, 24))
            
            # Introduction
            intro_text = (
                "The United States delegation to the United Nations Security Council expresses its "
                "commitment to addressing the critical issue of nuclear non-proliferation in the Middle East. "
                "Our position remains focused on promoting a weapons-free zone while ensuring regional "
                "security and stability."
            )
            content.append(Paragraph(intro_text, normal_style))
            content.append(Spacer(1, 12))
            
            # Body paragraphs
            body_text = (
                "Nuclear proliferation poses an existential threat to peace in the region. The United States "
                "supports a comprehensive approach to preventing the spread of nuclear weapons, maintaining "
                "the integrity of the Non-Proliferation Treaty, and working toward eventual disarmament."
            )
            content.append(Paragraph(body_text, normal_style))
            content.append(Spacer(1, 12))
            
            content.append(Paragraph("The United States supports the following key principles:", normal_style))
            content.append(Spacer(1, 6))
            
            principles = [
                "1. Strengthening the Non-Proliferation Treaty framework",
                "2. Encouraging diplomatic solutions to regional tensions",
                "3. Implementing robust verification mechanisms",
                "4. Supporting peaceful nuclear energy development"
            ]
            
            for principle in principles:
                content.append(Paragraph(principle, normal_style))
                content.append(Spacer(1, 6))
            
            content.append(Spacer(1, 6))
            
            conclusion = (
                "The delegation believes that international cooperation and multilateral agreements represent "
                "the best path forward for achieving lasting peace and security in the Middle East. We urge "
                "all parties to engage constructively in dialogue and confidence-building measures."
            )
            content.append(Paragraph(conclusion, normal_style))
            
            # Build and save the PDF
            doc.build(content)
            
            return output_path
            
        except ImportError:
            # If neither PyMuPDF nor ReportLab can create PDFs
            logger.error("Cannot create test PDF: neither PyMuPDF nor ReportLab is installed for PDF creation")
            raise ImportError("Cannot create test PDF: requires either PyMuPDF or ReportLab")


# Simple test if run directly
if __name__ == "__main__":
    import sys
    import argparse
    
    # Parse arguments
    parser = argparse.ArgumentParser(description='Process PDF documents')
    parser.add_argument('--input', help='Input PDF file path or S3 URI (s3://bucket/key)')
    parser.add_argument('--output', help='Output JSON file path or S3 URI (s3://bucket/key)')
    parser.add_argument('--test-mode', action='store_true', help='Run in test mode with simplified processing')
    parser.add_argument('--test-pdf', action='store_true', help='Create and use a test PDF')
    parser.add_argument('--memory-limit', type=int, default=0, help='Memory limit in MB (0 for no limit)')
    parser.add_argument('--max-pages', type=int, default=0, help='Maximum pages to process (0 for no limit)')
    parser.add_argument('--no-markdown', action='store_true', help='Disable markdown conversion')
    parser.add_argument('--document-type', help='Document type (position_paper, speech, etc.)')
    parser.add_argument('--aws', action='store_true', help='Force AWS mode for S3 operations')
    args = parser.parse_args()
    
    try:
        # Initialize processor
        processor = PDFProcessor(
            use_markdown=not args.no_markdown,
            test_mode=args.test_mode,
            memory_limit=args.memory_limit,
            max_pages=args.max_pages
        )
        
        # Process the PDF
        if args.test_pdf:
            # Create and use a test PDF
            test_pdf_path = create_test_pdf()
            print(f"Created test PDF: {test_pdf_path}")
            data = processor.process_pdf(test_pdf_path, args.document_type)
            
            # Save output
            if args.output:
                if args.output.startswith('s3://') and (AWS_AVAILABLE or args.aws):
                    # Parse S3 URI
                    s3_path = args.output[5:]  # Remove "s3://"
                    bucket, key = s3_path.split('/', 1)
                    
                    # Save to S3
                    s3_uri = processor.save_to_s3(data, bucket, key)
                    print(f"Saved result to {s3_uri}")
                else:
                    # Save to local file
                    output_path = processor.save_to_json(data, args.output)
                    print(f"Saved result to {output_path}")
            else:
                # Use default output path
                output_path = processor.save_to_json(data)
                print(f"Saved result to {output_path}")
            
        elif args.input:
            if args.input.startswith('s3://') and (AWS_AVAILABLE or args.aws):
                # Parse S3 URI
                s3_path = args.input[5:]  # Remove "s3://"
                bucket, key = s3_path.split('/', 1)
                
                print(f"Processing PDF from S3: s3://{bucket}/{key}")
                data = processor.process_pdf_from_s3(bucket, key, args.document_type)
                
                # Save output
                if args.output:
                    if args.output.startswith('s3://'):
                        # Parse S3 URI
                        output_s3_path = args.output[5:]  # Remove "s3://"
                        output_bucket, output_key = output_s3_path.split('/', 1)
                        
                        # Save to S3
                        s3_uri = processor.save_to_s3(data, output_bucket, output_key)
                        print(f"Saved result to {s3_uri}")
                    else:
                        # Save to local file
                        output_path = processor.save_to_json(data, args.output)
                        print(f"Saved result to {output_path}")
                else:
                    # Auto-generate S3 output path
                    output_key = key.rsplit('.', 1)[0] + "_processed.json"
                    s3_uri = processor.save_to_s3(data, bucket, output_key)
                    print(f"Saved result to {s3_uri}")
                
            else:
                # Local file
                print(f"Processing PDF: {args.input}")
                data = processor.process_pdf(args.input, args.document_type)
                
                # Save output
                if args.output:
                    if args.output.startswith('s3://') and (AWS_AVAILABLE or args.aws):
                        # Parse S3 URI
                        s3_path = args.output[5:]  # Remove "s3://"
                        bucket, key = s3_path.split('/', 1)
                        
                        # Save to S3
                        s3_uri = processor.save_to_s3(data, bucket, key)
                        print(f"Saved result to {s3_uri}")
                    else:
                        # Save to local file
                        output_path = processor.save_to_json(data, args.output)
                        print(f"Saved result to {output_path}")
                else:
                    # Use default output path
                    output_path = processor.save_to_json(data)
                    print(f"Saved result to {output_path}")
                
                # Print basic stats
                page_count = data["metadata"]["page_count"]
                processed_pages = data["metadata"]["processed_pages"]
                word_count = data["features"]["document_stats"]["word_count"]
                
                print(f"\nDocument Statistics:")
                print(f"  Pages: {processed_pages} of {page_count}")
                print(f"  Words: {word_count}")
                print(f"  Paragraphs: {data['features']['document_stats']['paragraph_count']}")
                print(f"  Sentences: {data['features']['document_stats']['sentence_count']}")
        
        else:
            print("No input specified. Use --input or --test-pdf")
            parser.print_help()
    
    except Exception as e:
        print(f"Error processing PDF: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


# AWS Lambda handler
def lambda_handler(event, context):
    """
    AWS Lambda handler for PDF processing
    
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
    event_info = {k: v for k, v in event.items() if k not in ['pdf_bytes', 'pdf_content']}
    logger.info(f"Processing Lambda event: {json.dumps(event_info)}")
    
    start_time = time.time()
    
    try:
        # Get configuration from event
        test_mode = event.get('test_mode', ENV_TEST_MODE)
        memory_limit = int(event.get('memory_limit', ENV_MEMORY_LIMIT))
        max_pages = int(event.get('max_pages', ENV_MAX_PAGES))
        use_markdown = event.get('use_markdown', ENV_USE_MARKDOWN)
        document_type = event.get('document_type')
        
        # Initialize processor
        processor = PDFProcessor(
            use_markdown=use_markdown,
            test_mode=test_mode,
            memory_limit=memory_limit,
            max_pages=max_pages
        )
        
        # Process PDF based on input type
        result = None
        
        if 'pdf_bytes' in event or 'pdf_content' in event:
            # Direct PDF bytes input (base64 encoded)
            pdf_bytes = event.get('pdf_bytes') or event.get('pdf_content')
            
            # Handle both string and binary format
            if isinstance(pdf_bytes, str):
                import base64
                pdf_bytes = base64.b64decode(pdf_bytes)
                
            filename = event.get('filename', 'document.pdf')
            result = processor.process_pdf_bytes(pdf_bytes, filename, document_type)
            
            # Save to S3 if output path specified
            if 'output_s3_bucket' in event and 'output_s3_key' in event:
                s3_uri = processor.save_to_s3(
                    result, 
                    event['output_s3_bucket'],
                    event['output_s3_key']
                )
                result["processing_metadata"]["output_uri"] = s3_uri
            
        elif 's3_bucket' in event and 's3_key' in event:
            # S3 input
            result = processor.process_pdf_from_s3(event['s3_bucket'], event['s3_key'], document_type)
            
            # Save to S3 if output path specified
            if 'output_s3_key' in event:
                s3_uri = processor.save_to_s3(
                    result, 
                    event.get('output_s3_bucket', event['s3_bucket']),
                    event['output_s3_key']
                )
                result["metadata"]["processing_metadata"]["output_uri"] = s3_uri
            
        elif 'test_pdf' in event and event['test_pdf']:
            # Use test PDF
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
                temp_path = temp_file.name
                
            test_pdf_path = create_test_pdf(temp_path)
            result = processor.process_pdf(test_pdf_path, document_type)
            
            # Clean up the temporary file
            try:
                os.unlink(temp_path)
            except Exception as e:
                logger.warning(f"Failed to delete temporary file {temp_path}: {e}")
            
        else:
            # Invalid input
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Invalid input. Must provide pdf_bytes, S3 path, or test_pdf flag.'
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
            'use_markdown': use_markdown,
            'memory_limit': memory_limit,
            'max_pages': max_pages,
            'timestamp': time.time()
        })
        
        # Report metrics
        if metrics:
            try:
                metrics['put_metric']('LambdaProcessingTime', processing_time, 'Seconds')
                metrics['put_metric']('LambdaInvocations', 1, 'Count')
                metrics['put_metric']('ProcessedPages', result["metadata"]["processed_pages"], 'Count')
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
