"""
Background Guide Processor Package

This package provides functionality for processing background guides,
extracting content, analyzing and summarizing text, and generating
structured outputs for RAG applications.
"""

from .processor import BackgroundGuideProcessor
from .extraction import extract_text_from_pdf, clean_text, extract_sections
from .segmentation import segment_document
from .summary import summarize_content, extract_key_insights
from .json_generator import generate_json_outputs
from .rag import create_vector_index, retrieve_context, build_rag_context 