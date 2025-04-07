"""
Train the Document Type Classifier with the papers in the papers directory.
This script will analyze papers to classify them as resolution, speech, or position paper.
"""

import os
import json
import argparse
import numpy as np
import torch
from tqdm import tqdm
import re

# Import our DocumentTypeClassifier
from distilbert_document_type_classifier import DocumentTypeClassifier, DOCUMENT_TYPES
from pdf_json import save_pdf_as_json

def create_initial_training_data():
    """
    Create initial training data with example documents of each type.
    This helps bootstrap the model when real labeled data is not available.
    
    Returns:
        list: List of (text, label) tuples for training
    """
    example_data = [
        # Resolutions (0)
        ("""DRAFT RESOLUTION
        The Security Council,
        Recalling its previous resolutions,
        Deeply concerned about recent developments,
        1. Calls upon all parties to cease hostilities;
        2. Decides to extend the mandate of the mission;
        3. Requests the Secretary-General to report within 90 days;""", 0),
        
        ("""RESOLUTION 2462 (2019)
        The Security Council,
        Reaffirming its primary responsibility for the maintenance of international peace and security,
        Reaffirming its resolutions 1267 (1999), 1373 (2001), and 1989 (2011),
        1. Decides that all States shall prevent and suppress the financing of terrorist acts;
        2. Urges all States to implement the FATF standards;
        3. Directs the Counter-Terrorism Committee to identify gaps in Member States' capacities;""", 0),
        
        # Speeches (1)
        ("""Thank you, Madam Chair.
        Distinguished delegates, it is my honor to address this committee today.
        The delegation of France believes that this issue requires our immediate attention.
        We would like to propose a three-part solution that addresses the root causes.
        I thank you for your attention.""", 1),
        
        ("""Thank you, Mr. President.
        I stand before you today representing the people of Brazil, a nation deeply committed to sustainable development.
        We believe that climate action must be balanced with economic needs.
        My delegation calls for increased financial support to developing nations.
        Thank you for your consideration.""", 1),
        
        # Position Papers (2)
        ("""POSITION PAPER
        Delegation: United Kingdom
        Committee: Security Council
        Topic A: Situation in the Middle East
        
        The United Kingdom recognizes the complexity of the situation in the Middle East.
        Our position is based on the following principles: sovereignty, dialogue, and multilateralism.
        The UK proposes the following solutions:
        1. Enhanced regional dialogue
        2. Economic development initiatives
        3. Security cooperation mechanisms""", 2),
        
        ("""POSITION PAPER
        Country: Germany
        Committee: DISEC
        Topic: Nuclear Disarmament
        
        The Federal Republic of Germany is committed to nuclear non-proliferation and disarmament.
        Germany believes in a world free of nuclear weapons and supports the implementation of the NPT.
        Germany puts forth the following recommendations:
        - Strengthen verification mechanisms
        - Promote confidence-building measures
        - Support nuclear-weapon-free zones""", 2)
    ]
    
    return example_data

def extract_document_type_from_filename(filename):
    """
    Try to determine document type from filename.
    
    Args:
        filename (str): Name of the file
    
    Returns:
        int or None: Document type index if identifiable, else None
    """
    filename_lower = filename.lower()
    
    # Check for common indicators in the filename
    if any(kw in filename_lower for kw in ["resolution", "draft", "final resolution"]):
        return 0  # Resolution
    elif any(kw in filename_lower for kw in ["speech", "speeches", "address", "statement"]):
        return 1  # Speech
    elif any(kw in filename_lower for kw in ["position paper", "position", "policy paper", "_position_"]):
        return 2  # Position paper
    
    return None  # Can't determine from filename

def user_label_document(document_name, preview_text):
    """
    Ask the user to label a document's type.
    
    Args:
        document_name (str): Name of the document
        preview_text (str): Preview of the document text
    
    Returns:
        int: Document type index
    """
    print(f"\nDocument: {document_name}")
    print(f"Preview: {preview_text[:200]}...\n")
    
    print("Document types:")
    for idx, doc_type in DOCUMENT_TYPES.items():
        print(f"{idx}: {doc_type}")
    
    while True:
        try:
            label = int(input("Enter document type number: "))
            if label in DOCUMENT_TYPES:
                return label
            print(f"Invalid input. Please enter a number between 0-{len(DOCUMENT_TYPES)-1}")
        except ValueError:
            print("Please enter a valid number.")

def process_pdf_directory(directory, output_dir=None, manual_labeling=False):
    """
    Process all PDFs in a directory to create training data.
    
    Args:
        directory (str): Directory containing PDF files
        output_dir (str, optional): Directory to save JSON files
        manual_labeling (bool): Whether to ask user for document type labels
    
    Returns:
        list: List of (text, label) tuples for training
    """
    if output_dir is None:
        output_dir = os.path.join(directory, "processed")
    
    os.makedirs(output_dir, exist_ok=True)
    
    training_data = []
    
    # Get all PDF files in the directory
    pdf_files = [f for f in os.listdir(directory) if f.lower().endswith('.pdf')]
    
    for pdf_file in tqdm(pdf_files, desc="Processing PDFs"):
        pdf_path = os.path.join(directory, pdf_file)
        json_path = os.path.join(output_dir, os.path.splitext(pdf_file)[0] + '.json')
        
        # Skip if JSON already exists
        if os.path.exists(json_path):
            print(f"JSON already exists for {pdf_file}. Loading...")
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            text = data['content']['main']
        else:
            # Process PDF to JSON (no need to ask about topics for training)
            print(f"Converting {pdf_file} to JSON...")
            json_path = save_pdf_as_json(pdf_path, json_path)
            
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            text = data['content']['main']
        
        # Determine document type
        doc_type = None
        
        if manual_labeling:
            # Ask user to label the document
            doc_type = user_label_document(pdf_file, text)
        else:
            # Try to determine from filename
            doc_type = extract_document_type_from_filename(pdf_file)
            
            # If can't determine from filename and classifier exists, use it
            if doc_type is None:
                # Try to instantiate classifier if it exists
                try:
                    classifier = DocumentTypeClassifier("./models/document-type-classifier")
                    doc_type_str, _ = classifier.predict(text, pdf_file)
                    for idx, type_str in DOCUMENT_TYPES.items():
                        if type_str == doc_type_str:
                            doc_type = idx
                            break
                except Exception as e:
                    print(f"Could not use classifier: {e}")
            
            # If still can't determine, ask user
            if doc_type is None:
                doc_type = user_label_document(pdf_file, text)
        
        # Add to training data
        training_data.append((text, doc_type))
        
        # Update JSON with document type
        data['document_type'] = DOCUMENT_TYPES[doc_type]
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
    
    return training_data

def main():
    parser = argparse.ArgumentParser(description='Train the document type classifier')
    parser.add_argument('--data_dir', type=str, default='./models/context-analysis/papers',
                        help='Directory containing PDF files')
    parser.add_argument('--output_dir', type=str, help='Directory to save processed JSON files')
    parser.add_argument('--epochs', type=int, default=3, help='Number of training epochs')
    parser.add_argument('--manual_labeling', action='store_true', 
                        help='Manually label all documents (otherwise tries to auto-detect)')
    parser.add_argument('--use_example_data', action='store_true', 
                        help='Use example data for training')
    args = parser.parse_args()
    
    training_data = []
    
    # Add example data if specified or if no real data is available
    if args.use_example_data:
        example_data = create_initial_training_data()
        training_data.extend(example_data)
        print(f"Using {len(example_data)} example documents for training")
    
    # Process PDFs in the data directory
    if args.data_dir and os.path.exists(args.data_dir):
        print(f"Processing PDFs in {args.data_dir}")
        pdf_data = process_pdf_directory(
            args.data_dir, 
            args.output_dir, 
            args.manual_labeling
        )
        training_data.extend(pdf_data)
        print(f"Processed {len(pdf_data)} PDFs from directory")
    
    if not training_data:
        print("No training data available. Please provide PDF files or use example data.")
        return
    
    # Split texts and labels
    texts = [item[0] for item in training_data]
    labels = [item[1] for item in training_data]
    
    # Initialize the classifier
    print(f"Preparing to train classifier with {len(training_data)} examples")
    classifier = DocumentTypeClassifier()
    
    # Train the model
    print("Starting training...")
    metrics = classifier.finetune(texts, labels, epochs=args.epochs)
    
    print(f"Training completed with metrics: {metrics}")
    print("Model saved to ./models/document-type-classifier")

if __name__ == "__main__":
    main() 