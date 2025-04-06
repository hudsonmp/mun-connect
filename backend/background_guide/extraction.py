"""
Text extraction module for background guide processing.

This module provides functions to extract text from PDF files and clean
the extracted text for further processing.
"""

import re
import fitz  # PyMuPDF

def extract_text_from_pdf(file_path: str) -> str:
    """
    Extract text from a PDF file.
    
    Args:
        file_path: Path to the PDF file
        
    Returns:
        Extracted text as a string
    """
    text = ""
    try:
        doc = fitz.open(file_path)
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text += page.get_text()
        doc.close()
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        raise
    
    return text

def clean_text(text: str) -> str:
    """
    Clean extracted text by removing extra whitespace, headers, footers, etc.
    
    Args:
        text: Raw text to clean
        
    Returns:
        Cleaned text
    """
    # Replace multiple newlines with a single newline
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Remove page numbers (common formats)
    text = re.sub(r'\n\s*\d+\s*\n', '\n', text)
    text = re.sub(r'\n\s*Page \d+\s*\n', '\n', text)
    
    # Remove headers and footers (simplified approach)
    # This is a basic approach; more sophisticated methods would be needed
    # for complex documents with varying headers/footers
    lines = text.split('\n')
    cleaned_lines = []
    header_pattern = re.compile(r'^(header|title|conference|committee|session)', re.IGNORECASE)
    footer_pattern = re.compile(r'^(footer|copyright|all rights reserved|confidential)', re.IGNORECASE)
    
    for line in lines:
        # Skip very short lines that might be page numbers
        if len(line.strip()) < 3:
            continue
        
        # Skip lines that look like headers or footers
        if header_pattern.search(line) or footer_pattern.search(line):
            continue
        
        cleaned_lines.append(line)
    
    cleaned_text = '\n'.join(cleaned_lines)
    
    # Additional cleaning
    # Remove extra spaces
    cleaned_text = re.sub(r' {2,}', ' ', cleaned_text)
    
    # Remove leading/trailing whitespace from lines
    cleaned_text = '\n'.join([line.strip() for line in cleaned_text.split('\n')])
    
    return cleaned_text

def extract_sections(text: str) -> list:
    """
    Extract sections from text based on headings.
    
    Args:
        text: Text to extract sections from
        
    Returns:
        List of dictionaries containing section titles and content
    """
    # Simple rule-based approach to find sections
    # This is a basic implementation and might need refinement for complex documents
    
    # Identify potential headings (all caps lines or lines ending with ":")
    lines = text.split('\n')
    sections = []
    current_section = {"title": "Introduction", "content": ""}
    
    for line in lines:
        line = line.strip()
        
        # Skip empty lines
        if not line:
            continue
        
        # Check if line is a potential heading
        is_heading = False
        
        # Check for all caps lines that aren't too long (likely headings)
        if line.isupper() and len(line) < 100:
            is_heading = True
        
        # Check for lines ending with colon
        if line.endswith(':') and len(line) < 100:
            is_heading = True
        
        # Check for numbered headings (e.g., "1. Introduction")
        if re.match(r'^\d+\.\s+[A-Z]', line):
            is_heading = True
        
        if is_heading:
            # Save previous section if it has content
            if current_section["content"]:
                sections.append(current_section)
            
            # Start new section
            current_section = {"title": line, "content": ""}
        else:
            # Add line to current section
            current_section["content"] += line + "\n"
    
    # Add the last section
    if current_section["content"]:
        sections.append(current_section)
    
    return sections 