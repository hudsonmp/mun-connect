# Use PyTorch and transformers for NER
from transformers import AutoTokenizer, AutoModelForTokenClassification
import torch
import json
import os
import re
from typing import Dict, List, Optional, Set

# Initialize the model and tokenizer
model_name = "dslim/bert-base-NER"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForTokenClassification.from_pretrained(model_name)

# Move model to GPU if available
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = model.to(device)

def preprocess_text(text: str) -> str:
    """
    Preprocess text to improve entity detection.
    """
    # Fix common PDF extraction issues
    text = text.replace("\n", " ")
    text = re.sub(r'\s+', ' ', text)
    text = text.replace("'", "'")
    
    # Fix common word joining issues
    text = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', text)
    text = re.sub(r'(?<=[A-Z])(?=[A-Z][a-z])', ' ', text)
    
    return text.strip()

def extract_sources(text: str) -> List[str]:
    """
    Extract sources from text using various citation patterns.
    """
    sources = set()
    
    # Common citation patterns
    patterns = [
        r'\(([^)]+?\d{4}[^)]+?)\)',  # (Author, 2024) or (Author et al., 2024)
        r'([A-Z][a-z]+(?:\s+(?:et\s+al\.|\&|\and)\s+[A-Z][a-z]+)?)\s+\(\d{4}\)',  # Author (2024) or Author et al. (2024)
        r'(?:^|\s)([A-Z][a-z]+\s+(?:et\s+al\.)?,\s+\d{4})',  # Author, 2024 or Author et al., 2024
        r'(?:cited\s+in|according\s+to)\s+([A-Z][a-z]+(?:\s+et\s+al\.)?(?:\s+\(\d{4}\)|\s*,\s*\d{4}))',  # cited in Author (2024)
        r'(?:^|\s)((?:https?://|www\.)[^\s]+)',  # URLs
        r'(?:^|\s)([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+\d{4})',  # Organization 2024
        r'(?:^|\s)([A-Z][a-z]+(?:\s+and\s+[A-Z][a-z]+)?\s+\d{4})',  # Author and Author 2024
        r'(?:^|\s)([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+et\s+al\.\s+\d{4})',  # Author et al. 2024
    ]
    
    for pattern in patterns:
        matches = re.finditer(pattern, text, re.MULTILINE)
        for match in matches:
            source = match.group(1).strip()
            if source:
                sources.add(source)
    
    return list(sources)

def process_entities(text: str) -> Dict:
    """
    Process text through NER pipeline and extract relevant entities using PyTorch.
    Returns a structured dictionary of found entities.
    """
    # Preprocess text
    text = preprocess_text(text)
    
    # Split text into chunks to handle long documents
    max_length = 512
    words = text.split()
    chunks = []
    current_chunk = []
    current_length = 0
    
    for word in words:
        word_tokens = tokenizer.tokenize(word)
        if current_length + len(word_tokens) > max_length:
            chunks.append(' '.join(current_chunk))
            current_chunk = [word]
            current_length = len(word_tokens)
        else:
            current_chunk.append(word)
            current_length += len(word_tokens)
    
    if current_chunk:
        chunks.append(' '.join(current_chunk))
    
    # Initialize entity categories
    entities = {
        "committee": None,
        "character": None,
        "country": None,
        "topic": None,
        "sub_topic": None,
        "committee_type": None,
        "timeframe": None,
        "sources": []
    }
    
    # Process each chunk
    all_entities = []
    for chunk in chunks:
        # Tokenize the input text
        inputs = tokenizer(chunk, return_tensors="pt", padding=True, truncation=True, max_length=512)
        inputs = {k: v.to(device) for k, v in inputs.items()}
        
        # Get predictions
        with torch.no_grad():
            outputs = model(**inputs)
            predictions = torch.argmax(outputs.logits, dim=2)
        
        # Convert predictions to labels
        predicted_labels = [model.config.id2label[t.item()] for t in predictions[0]]
        tokens = tokenizer.convert_ids_to_tokens(inputs["input_ids"][0])
        
        # Process predictions
        current_entity = ""
        current_type = ""
        
        for token, label in zip(tokens, predicted_labels):
            if label.startswith("B-"):  # Beginning of entity
                if current_entity:  # Store previous entity if exists
                    all_entities.append((current_entity.strip(), current_type))
                current_type = label[2:]  # Remove "B-" prefix
                current_entity = token.replace("##", "")
            elif label.startswith("I-"):  # Inside of entity
                current_entity += " " + token.replace("##", "")
            elif current_entity:  # End of entity
                all_entities.append((current_entity.strip(), current_type))
                current_entity = ""
                current_type = ""
    
    # Store all found entities
    for entity_text, entity_type in all_entities:
        _store_entity(entities, entity_text, entity_type)
    
    # Extract sources
    entities["sources"] = extract_sources(text)
    
    return entities

def _store_entity(entities: Dict, entity_text: str, entity_type: str) -> None:
    """
    Helper function to store entities in the appropriate category.
    """
    # Clean up entity text
    entity_text = entity_text.replace("[CLS]", "").replace("[SEP]", "").strip()
    if not entity_text or len(entity_text) < 2:  # Ignore very short entities
        return
    
    # Map entity types to categories
    if entity_type == "ORG" and not entities["committee"]:
        if any(keyword in entity_text.lower() for keyword in ["committee", "council", "assembly"]):
            entities["committee"] = entity_text
    elif entity_type == "PER" and not entities["character"]:
        if len(entity_text.split()) >= 2:  # Only store full names
            entities["character"] = entity_text
    elif entity_type == "LOC" and not entities["country"]:
        if len(entity_text.split()) <= 3:  # Avoid long location descriptions
            entities["country"] = entity_text
    elif entity_type == "MISC":
        # Try to categorize MISC entities
        if not entities["topic"] and any(keyword in entity_text.lower() for keyword in ["policy", "rights", "security", "economy", "crisis"]):
            entities["topic"] = entity_text
        elif not entities["timeframe"] and any(keyword in entity_text.lower() for keyword in ["year", "century", "decade", "2024", "2023"]):
            entities["timeframe"] = entity_text

def get_missing_entities(entities: Dict) -> Dict:
    """
    Handle missing entities by prompting the user for input.
    """
    for key, value in entities.items():
        if key == "sources":
            if not value:  # If sources list is empty
                while True:
                    source = input("No sources detected. Enter a source (or press Enter to skip): ")
                    if not source.strip():
                        break
                    entities["sources"].append(source.strip())
        elif value is None:
            user_input = input(f"Could not detect {key}. Please provide it: ")
            entities[key] = user_input.strip()
    
    return entities

def process_json_file(json_file_path: str) -> str:
    """
    Process a JSON file containing document text and update it with entity information.
    
    Args:
        json_file_path (str): Path to the JSON file
        
    Returns:
        str: Path to the updated JSON file
    """
    try:
        # Read the JSON file
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Process each document in the JSON
        for doc_name, text in data.items():
            if isinstance(text, str):
                # Get entities from NER
                entities = process_entities(text)
                
                # Handle missing entities
                entities = get_missing_entities(entities)
                
                # Add entities to the JSON data
                data[doc_name] = {
                    "text": text,
                    "entities": entities
                }
        
        # Write the updated JSON back to the file
        with open(json_file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        
        return json_file_path
    
    except Exception as e:
        print(f"Error processing JSON file: {e}")
        return None

# Example usage:
if __name__ == "__main__":
    json_file = input("Enter path to JSON file: ")
    if os.path.exists(json_file):
        updated_file = process_json_file(json_file)
        if updated_file:
            print(f"Successfully processed and updated {updated_file}")
    else:
        print(f"File not found: {json_file}")