import os
import json
from pdf_json import save_pdf_as_json
from typing import Dict, List

def process_papers_to_json(papers_dir: str, output_file: str = "training_data.json") -> str:
    """
    Process all PDF papers in a directory and create a JSON file for labeling.
    
    Args:
        papers_dir: Directory containing the PDF papers
        output_file: Path to save the output JSON file
        
    Returns:
        str: Path to the created JSON file
    """
    training_data = {}
    
    # Process each PDF file in the directory
    for filename in os.listdir(papers_dir):
        if filename.endswith(".pdf"):
            pdf_path = os.path.join(papers_dir, filename)
            print(f"\nProcessing {filename}...")
            
            # Convert PDF to JSON
            json_path = save_pdf_as_json(pdf_path)
            
            # Read the JSON content
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Get the text content
            text = next(iter(data.values()))  # Get the first (and only) value from the dict
            
            # Create template for manual labeling
            training_data[filename] = {
                "text": text,
                "entities": {
                    "committee": [],  # Format: [[start_idx, end_idx, "text"]]
                    "character": [],
                    "country": [],
                    "topic": [],
                    "sub_topic": [],
                    "committee_type": [],
                    "timeframe": [],
                    "sources": []
                }
            }
            
            # Clean up temporary JSON file
            os.remove(json_path)
    
    # Save the training data template
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(training_data, f, indent=4, ensure_ascii=False)
    
    print(f"\nCreated training data template at: {output_file}")
    print("\nPlease label the entities in the JSON file with their start and end indices.")
    print("Example format for entities:")
    print('''
    "committee": [
        [4, 35, "Economic and Financial Committee"],
        [71, 86, "General Assembly"]
    ]
    ''')
    
    return output_file

def validate_labeled_data(json_file: str) -> bool:
    """
    Validate that the labeled data is properly formatted.
    
    Args:
        json_file: Path to the labeled JSON file
        
    Returns:
        bool: True if validation passes
    """
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for doc_name, doc_data in data.items():
            text = doc_data["text"]
            entities = doc_data["entities"]
            
            # Check each entity type
            for entity_type, entity_list in entities.items():
                if entity_type != "sources":  # Sources are handled differently
                    for start_idx, end_idx, entity_text in entity_list:
                        # Verify indices are valid
                        if not (isinstance(start_idx, int) and isinstance(end_idx, int)):
                            print(f"Error in {doc_name}: Invalid indices for {entity_type}")
                            return False
                        
                        # Verify text matches
                        if text[start_idx:end_idx] != entity_text:
                            print(f"Error in {doc_name}: Text mismatch for {entity_type}")
                            print(f"Expected: {entity_text}")
                            print(f"Found: {text[start_idx:end_idx]}")
                            return False
        
        print("Validation successful! The labeled data is properly formatted.")
        return True
        
    except Exception as e:
        print(f"Error validating labeled data: {e}")
        return False

if __name__ == "__main__":
    # Directory containing your PDF papers
    papers_dir = "papers"
    
    # Create the papers directory if it doesn't exist
    os.makedirs(papers_dir, exist_ok=True)
    
    print("Please put your PDF papers in the 'papers' directory.")
    input("Press Enter when ready...")
    
    if not os.listdir(papers_dir):
        print("No PDF files found in the papers directory!")
    else:
        # Create the training data template
        json_file = process_papers_to_json(papers_dir)
        
        print("\nPlease label the entities in the JSON file.")
        print("After labeling, run this script again to validate the labels.")
        
        # If the file exists and user says it's labeled, validate it
        if os.path.exists(json_file):
            labeled = input("\nHave you finished labeling the data? (y/n): ")
            if labeled.lower() == 'y':
                validate_labeled_data(json_file) 