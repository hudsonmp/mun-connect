"""
Validator functions for AI responses in the MUN-Connect platform.
These validators can be used with AIInterface.generate_with_validation.
"""
import json
import re
from typing import Dict, List, Union, Any


def is_valid_json(text: str) -> bool:
    """Check if text is valid JSON"""
    try:
        json.loads(text)
        return True
    except:
        return False


def json_matches_schema(text: str, schema: Dict[str, Any]) -> bool:
    """
    Check if JSON matches a simple schema definition
    
    Args:
        text: JSON text to validate
        schema: Simple schema defining required fields and types
               e.g. {"name": str, "age": int, "scores": list}
    
    Returns:
        True if JSON matches schema, False otherwise
    """
    try:
        data = json.loads(text)
        
        # Check if all required fields exist with correct types
        for field, expected_type in schema.items():
            if field not in data:
                return False
            
            # Handle special case for lists of specific types
            if isinstance(expected_type, list) and len(expected_type) == 1:
                if not isinstance(data[field], list):
                    return False
                # Check each item in the list
                item_type = expected_type[0]
                if not all(isinstance(item, item_type) for item in data[field]):
                    return False
            # Handle special case for dictionaries with specific types
            elif isinstance(expected_type, dict):
                if not isinstance(data[field], dict):
                    return False
                # Additional dictionary validation could be added here
            # Regular type checking
            elif not isinstance(data[field], expected_type):
                return False
                
        return True
    except:
        return False


def has_required_sections(text: str, sections: List[str]) -> bool:
    """
    Check if text contains all required sections
    
    Args:
        text: Text to check
        sections: List of section headings to look for
    
    Returns:
        True if all sections are present, False otherwise
    """
    for section in sections:
        # Look for section headings (case insensitive)
        pattern = re.compile(f"{section}\\s*:|\#{1,6}\\s*{section}", re.IGNORECASE)
        if not pattern.search(text):
            return False
    return True


def has_max_word_count(text: str, max_words: int) -> bool:
    """Check if text has at most max_words words"""
    words = text.split()
    return len(words) <= max_words


def has_min_word_count(text: str, min_words: int) -> bool:
    """Check if text has at least min_words words"""
    words = text.split()
    return len(words) >= min_words


def has_citation_format(text: str, citation_format: str = "any") -> bool:
    """
    Check if text contains citations in the required format
    
    Args:
        text: Text to check
        citation_format: Citation format to check for ("apa", "mla", "chicago", "any")
    
    Returns:
        True if citations are present in the required format, False otherwise
    """
    if citation_format == "apa":
        return bool(re.search(r'\(\w+, \d{4}\)', text))
    elif citation_format == "mla":
        return bool(re.search(r'\(\w+ \d+\)', text))
    elif citation_format == "chicago":
        return bool(re.search(r'\d+\. ', text))
    else:  # "any"
        return bool(re.search(r'\(.*\d{4}.*\)', text) or re.search(r'\d+\. ', text)) 