"""
Segmentation module for background guide processing.

This module provides functions to segment a document into logical sections
based on headings, subheadings, and paragraph breaks.
"""

import re
import torch
from typing import Dict, List, Optional
from transformers import AutoTokenizer, AutoModelForSequenceClassification

def segment_document(
    text: str, 
    tokenizer: Optional[AutoTokenizer] = None, 
    model: Optional[AutoModelForSequenceClassification] = None
) -> List[Dict[str, str]]:
    """
    Segment a document into logical sections.
    
    This function uses a combination of rule-based and ML-based approaches
    to segment the document into sections based on headings and content.
    
    Args:
        text: The text to segment
        tokenizer: Optional pre-loaded tokenizer for ML-based segmentation
        model: Optional pre-loaded model for ML-based segmentation
        
    Returns:
        List of dictionaries containing section information
    """
    # First attempt rule-based segmentation
    rule_based_segments = rule_based_segmentation(text)
    
    # If we have a model and tokenizer, refine the segments using ML
    if tokenizer is not None and model is not None:
        segments = ml_based_segmentation(rule_based_segments, tokenizer, model)
    else:
        segments = rule_based_segments
    
    return segments

def rule_based_segmentation(text: str) -> List[Dict[str, str]]:
    """
    Segment a document using rule-based approaches.
    
    Args:
        text: The text to segment
        
    Returns:
        List of segmentation results
    """
    segments = []
    
    # Split by common heading patterns
    lines = text.split('\n')
    current_heading = "Introduction"
    current_subheading = None
    current_text = ""
    level = 1  # Start with level 1 (main heading)
    
    for line in lines:
        line = line.strip()
        
        # Skip empty lines
        if not line:
            current_text += "\n"
            continue
        
        # Check for main heading patterns
        if (line.isupper() and len(line) > 3 and len(line) < 100) or \
           re.match(r'^[IVX]+\.\s+', line) or \
           re.match(r'^\d+\.\s+[A-Z]', line):
            
            # Save current segment if we have text
            if current_text.strip():
                segments.append({
                    "section": current_heading,
                    "subsection": current_subheading,
                    "text": current_text.strip(),
                    "level": level
                })
            
            # Start new segment
            current_heading = line
            current_subheading = None
            current_text = ""
            level = 1
            continue
        
        # Check for subheading patterns
        if re.match(r'^[a-z]\)\s+', line) or \
           re.match(r'^\d+\.\d+\.\s+', line) or \
           (line.endswith(':') and len(line) < 100):
            
            # Save current segment if we have text
            if current_text.strip():
                segments.append({
                    "section": current_heading,
                    "subsection": current_subheading,
                    "text": current_text.strip(),
                    "level": level
                })
            
            # Start new segment
            current_subheading = line
            current_text = ""
            level = 2
            continue
        
        # Otherwise, add line to current text
        current_text += line + "\n"
    
    # Add the final segment
    if current_text.strip():
        segments.append({
            "section": current_heading,
            "subsection": current_subheading,
            "text": current_text.strip(),
            "level": level
        })
    
    # If no segments were created, create a single segment with all text
    if not segments:
        segments.append({
            "section": "Document",
            "subsection": None,
            "text": text.strip(),
            "level": 1
        })
    
    return segments

def ml_based_segmentation(
    rule_segments: List[Dict[str, str]],
    tokenizer: AutoTokenizer,
    model: AutoModelForSequenceClassification
) -> List[Dict[str, str]]:
    """
    Refine rule-based segments using ML model predictions.
    
    Args:
        rule_segments: Segments from rule-based approach
        tokenizer: Tokenizer for the ML model
        model: Classification model for segment refinement
        
    Returns:
        Refined segments
    """
    refined_segments = []
    
    for segment in rule_segments:
        # If the segment is short, keep it as is
        if len(segment["text"].split()) < 50:
            refined_segments.append(segment)
            continue
        
        # Split long segments into paragraphs
        paragraphs = re.split(r'\n{2,}', segment["text"])
        
        # For very long segments, check if they should be split further
        if len(paragraphs) > 1:
            for i, para in enumerate(paragraphs):
                # Skip very short paragraphs
                if len(para.split()) < 15:
                    continue
                
                # Classify if this paragraph is a new section
                is_new_section = classify_as_heading(para, tokenizer, model)
                
                if is_new_section and i > 0:
                    # Create a new segment with this paragraph as heading
                    first_line = para.split('\n')[0]
                    refined_segments.append({
                        "section": segment["section"],
                        "subsection": first_line,
                        "text": para,
                        "level": segment["level"] + 1
                    })
                else:
                    # Add to the current segment
                    refined_segments.append({
                        "section": segment["section"],
                        "subsection": segment["subsection"],
                        "text": para,
                        "level": segment["level"]
                    })
        else:
            # Keep the segment as is
            refined_segments.append(segment)
    
    return refined_segments

def classify_as_heading(text: str, tokenizer: AutoTokenizer, model: AutoModelForSequenceClassification) -> bool:
    """
    Classify text as heading or not using a pre-trained model.
    
    Args:
        text: Text to classify
        tokenizer: Pre-trained tokenizer
        model: Pre-trained classification model
        
    Returns:
        Boolean indicating if the text is likely a heading
    """
    # Use just the first line or first 100 characters
    first_line = text.split('\n')[0]
    sample = first_line[:100]
    
    # Tokenize the text
    inputs = tokenizer(sample, return_tensors="pt", truncation=True, padding=True)
    
    # Move inputs to the same device as the model
    device = next(model.parameters()).device
    inputs = {k: v.to(device) for k, v in inputs.items()}
    
    # Get model prediction
    with torch.no_grad():
        outputs = model(**inputs)
        logits = outputs.logits
        probabilities = torch.softmax(logits, dim=1)
        prediction = torch.argmax(probabilities, dim=1).item()
    
    # Assuming binary classification where 1 = heading, 0 = not heading
    return prediction == 1 