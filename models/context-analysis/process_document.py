import os
import sys
from typing import Optional

# Add the current directory to Python path to find the modules
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# Now we can import our local modules
from pdf_json import save_pdf_as_json
sys.path.append(os.path.join(current_dir, "bert_base_NER"))
from pipleine import process_json_file

def process_pdf_document(pdf_path: str) -> Optional[str]:
    """
    Process a PDF document through the entire pipeline:
    1. Convert PDF to JSON
    2. Process the JSON through NER to extract entities
    
    Args:
        pdf_path (str): Path to the PDF file
        
    Returns:
        Optional[str]: Path to the final processed JSON file with entities, or None if error occurs
    """
    try:
        print(f"Processing PDF document: {pdf_path}")
        
        # Step 1: Convert PDF to JSON
        print("\nStep 1: Converting PDF to JSON...")
        json_path = save_pdf_as_json(pdf_path)
        if not json_path:
            raise Exception("Failed to convert PDF to JSON")
        print(f"PDF converted to JSON: {json_path}")
        
        # Step 2: Process JSON through NER pipeline
        print("\nStep 2: Extracting entities...")
        processed_json = process_json_file(json_path)
        if not processed_json:
            raise Exception("Failed to extract entities")
        print(f"Entities extracted and saved to: {processed_json}")
        
        return processed_json
        
    except Exception as e:
        print(f"Error processing document: {e}")
        return None

if __name__ == "__main__":
    # Process the ECOFIN_CHINA.pdf document
    current_dir = os.path.dirname(os.path.abspath(__file__))
    pdf_file = os.path.join(current_dir, "ECOFIN_CHINA.pdf")
    
    if os.path.exists(pdf_file):
        result = process_pdf_document(pdf_file)
        if result:
            print(f"\nDocument successfully processed! Final output: {result}")
        else:
            print("Failed to process the document.")
    else:
        print(f"Error: Could not find the file {pdf_file}") 