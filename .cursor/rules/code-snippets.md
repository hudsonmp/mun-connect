# Code Snippets for Tricky Implementation

This document provides essential code snippets for the most critical and potentially challenging parts of the Model UN Assistant platform. These snippets are fully functional and tested to ensure they work as expected.

## Table of Contents

1. [OpenAI Integration](#openai-integration)
2. [Document Parsing](#document-parsing)
3. [TinyMCE Integration](#tinymce-integration)
4. [Supabase Authentication](#supabase-authentication)
5. [File Upload and Processing](#file-upload-and-processing)
6. [Error Handling and Retry Logic](#error-handling-and-retry-logic)
7. [Rate Limiting Implementation](#rate-limiting-implementation)
8. [Document Export Logic](#document-export-logic)

## OpenAI Integration

### Optimized Prompt for Position Paper Generation

```python
# backend/services/openai_service.py
import os
import openai
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class OpenAIService:
    def __init__(self):
        openai.api_key = os.environ.get("OPENAI_API_KEY")
        self.model = os.environ.get("OPENAI_MODEL", "gpt-3.5-turbo")
        self.max_tokens = 4096
        self.temperature = 0.7

    def generate_position_paper(
        self,
        committee: str,
        country: str,
        topic: str,
        background_text: Optional[str] = None,
        additional_context: Optional[str] = None
    ) -> Dict:
        """
        Generate a position paper using OpenAI's API.
        
        Args:
            committee: The committee name
            country: The country being represented
            topic: The topic of discussion
            background_text: Extracted text from background guide
            additional_context: Additional instructions or context
            
        Returns:
            Dict containing generated content and metadata
        """
        try:
            system_prompt = """You are an expert Model UN advisor helping a high school student create a position paper. 
            Create a formal, well-researched position paper following standard Model UN format. 
            The paper should be 2-3 pages (about 1000-1500 words) and include:
            
            1. A header with committee name, country, and topic
            2. An introduction that states the country's position on the topic
            3. A body that outlines 2-3 specific policy proposals with supporting evidence
            4. A conclusion summarizing the country's stance and proposed solutions
            
            Use formal diplomatic language appropriate for Model UN. Include specific policies and actions 
            that align with the country's actual foreign policy and national interests. If background 
            information is provided, incorporate relevant details from it.
            
            Format the document with proper HTML tags for headings, paragraphs, and lists."""

            user_prompt = f"Committee: {committee}\nCountry: {country}\nTopic: {topic}\n"
            
            if background_text:
                # Truncate background text if it's too long
                if len(background_text) > 6000:
                    background_text = background_text[:6000] + "... [text truncated for length]"
                user_prompt += f"\nBackground Guide Information:\n{background_text}\n"
            
            if additional_context:
                user_prompt += f"\nAdditional Context:\n{additional_context}\n"
            
            user_prompt += "\nPlease generate a complete position paper in HTML format."

            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            content = response.choices[0].message.content
            
            # Add wrapper div with class for styling
            html_content = f"<div class='position-paper'>{content}</div>"
            
            return {
                "content": html_content,
                "title": f"Position Paper: {country} on {topic}",
                "tokens": {
                    "prompt": response.usage.prompt_tokens,
                    "completion": response.usage.completion_tokens,
                    "total": response.usage.total_tokens
                }
            }
            
        except openai.error.OpenAIError as e:
            logger.error(f"OpenAI API error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in generate_position_paper: {str(e)}")
            raise

    # Add fallback method for when primary generation fails
    def generate_position_paper_fallback(
        self,
        committee: str,
        country: str,
        topic: str
    ) -> Dict:
        """Simplified generation without reference materials for fallback"""
        try:
            # Use more concise prompt and gpt-3.5-turbo for reliability
            system_prompt = "Create a basic Model UN position paper with header, introduction, body, and conclusion."
            user_prompt = f"Create a position paper for {country} in {committee} on the topic: {topic}."
            
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",  # Use more reliable model for fallback
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=2048,  # Reduce token count for faster response
                temperature=0.5  # Lower temperature for more predictable output
            )
            
            content = response.choices[0].message.content
            
            return {
                "content": f"<div class='position-paper'>{content}</div>",
                "title": f"Position Paper: {country} on {topic} (Basic Version)",
                "tokens": {
                    "prompt": response.usage.prompt_tokens,
                    "completion": response.usage.completion_tokens,
                    "total": response.usage.total_tokens
                },
                "fallback": True
            }
            
        except Exception as e:
            logger.error(f"Fallback generation failed: {str(e)}")
            raise
```

## Document Parsing

### Extracting Text from PDF and DOCX Files

```python
# backend/utils/document_parser.py
import io
import os
import logging
from typing import Dict, Optional

import PyPDF2
import docx

logger = logging.getLogger(__name__)

def extract_text_from_file(file_data: bytes, file_type: str) -> Optional[str]:
    """
    Extract text content from various file types.
    
    Args:
        file_data: Binary file data
        file_type: MIME type of file
        
    Returns:
        Extracted text or None if extraction fails
    """
    try:
        if file_type == 'application/pdf':
            return extract_from_pdf(file_data)
        elif file_type in ['application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/msword']:
            return extract_from_docx(file_data)
        elif file_type == 'text/plain':
            return file_data.decode('utf-8', errors='replace')
        else:
            logger.warning(f"Unsupported file type for extraction: {file_type}")
            return None
    except Exception as e:
        logger.error(f"Error extracting text from file: {str(e)}")
        return None

def extract_from_pdf(file_data: bytes) -> str:
    """Extract text from a PDF file"""
    text = ""
    try:
        pdf_file = io.BytesIO(file_data)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        
        # Simple extraction with text sanitization
        for page_num in range(len(pdf_reader.pages)):
            page = pdf_reader.pages[page_num]
            page_text = page.extract_text()
            
            # Basic text cleanup
            if page_text:
                # Replace multiple spaces and newlines
                cleaned_text = ' '.join(page_text.split())
                text += cleaned_text + "\n\n"
        
        return text.strip()
    except Exception as e:
        logger.error(f"PDF extraction error: {str(e)}")
        # Return partial text if available
        return text if text else ""

def extract_from_docx(file_data: bytes) -> str:
    """Extract text from a DOCX file"""
    text = ""
    try:
        doc_file = io.BytesIO(file_data)
        doc = docx.Document(doc_file)
        
        # Extract text from paragraphs
        for para in doc.paragraphs:
            if para.text:
                text += para.text + "\n"
        
        # Extract text from tables
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    if cell.text:
                        text += cell.text + " "
                text += "\n"
        
        return text.strip()
    except Exception as e:
        logger.error(f"DOCX extraction error: {str(e)}")
        # Return partial text if available
        return text if text else ""
```

## TinyMCE Integration

### React Component with TinyMCE Editor

```jsx
// frontend/components/DocumentEditor.jsx
import React, { useState, useEffect, useRef } from 'react';
import { Editor } from '@tinymce/tinymce-react';

// Simple autosave indicator component
const AutosaveIndicator = ({ status }) => {
  const statusColors = {
    saved: 'bg-green-500',
    saving: 'bg-yellow-500',
    error: 'bg-red-500',
    idle: 'bg-gray-400',
  };
  
  return (
    <div className="flex items-center mt-1">
      <div className={`w-2 h-2 rounded-full mr-2 ${statusColors[status]}`}></div>
      <span className="text-xs text-gray-600">
        {status === 'saved' && 'All changes saved'}
        {status === 'saving' && 'Saving...'}
        {status === 'error' && 'Save failed'}
        {status === 'idle' && 'Ready'}
      </span>
    </div>
  );
};

const DocumentEditor = ({ 
  initialContent, 
  documentId,
  onSave,
  readOnly = false
}) => {
  const [content, setContent] = useState(initialContent || '');
  const [saveStatus, setSaveStatus] = useState('idle');
  const [charCount, setCharCount] = useState(0);
  const editorRef = useRef(null);
  const saveTimeoutRef = useRef(null);
  
  // Calculate character count when content changes
  useEffect(() => {
    // Strip HTML tags to get accurate character count
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = content;
    const textContent = tempDiv.textContent || tempDiv.innerText || '';
    setCharCount(textContent.length);
  }, [content]);
  
  // Autosave functionality
  useEffect(() => {
    // Don't save if editor is in read-only mode or no content changes
    if (readOnly || !content || content === initialContent) return;
    
    // Clear any pending save timeout
    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current);
    }
    
    // Set a timeout for debouncing saves (1 second after typing stops)
    saveTimeoutRef.current = setTimeout(() => {
      handleSave();
    }, 1000);
    
    return () => {
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current