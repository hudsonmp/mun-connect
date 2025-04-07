"""
Train the Document Type Classifier from existing processed JSON files.
This script assumes documents are already classified in the processed directory.
"""

import os
import json
import argparse
import torch
import numpy as np
from tqdm import tqdm
import sys
from transformers import TrainingArguments

# Add the current directory to Python path to find the modules
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# Import our DocumentTypeClassifier
from distilbert_document_type_classifier import DocumentTypeClassifier, DOCUMENT_TYPES

def load_processed_json_data(processed_dir):
    """
    Load data from processed JSON files.
    
    Args:
        processed_dir (str): Directory containing processed JSON files
    
    Returns:
        list: List of (text, label) tuples for training
    """
    training_data = []
    
    # Get all JSON files in the directory
    json_files = [f for f in os.listdir(processed_dir) if f.lower().endswith('.json')]
    
    # Document type mapping
    doc_type_to_idx = {doc_type: idx for idx, doc_type in DOCUMENT_TYPES.items()}
    
    print(f"Found {len(json_files)} JSON files for training")
    
    for json_file in tqdm(json_files, desc="Loading JSON files"):
        file_path = os.path.join(processed_dir, json_file)
        
        try:
            # Load JSON
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Check if it's multi-topic
            is_multi_topic = data.get('multi_topic', False)
            
            # Determine document type based on filename and content
            doc_type = determine_document_type(json_file, data)
            
            # Convert document type string to index
            doc_type_idx = doc_type_to_idx.get(doc_type)
            
            if doc_type_idx is None:
                print(f"Warning: Unknown document type '{doc_type}' in {json_file}")
                continue
            
            if is_multi_topic:
                # Process each topic as a separate document
                content = data.get('content', {})
                for topic_name, text in content.items():
                    if text.strip():  # Only add non-empty texts
                        training_data.append((text, doc_type_idx))
            else:
                # Single topic document
                text = data.get('content', {}).get('main', '')
                if text.strip():  # Only add non-empty texts
                    training_data.append((text, doc_type_idx))
        
        except Exception as e:
            print(f"Error processing {json_file}: {e}")
    
    return training_data

def determine_document_type(filename, data):
    """
    Determine document type based on the filename and content.
    
    Args:
        filename (str): Name of the file
        data (dict): JSON data
    
    Returns:
        str: Document type
    """
    # Check if document type is already present in the data
    if 'document_type' in data:
        return data['document_type']
    
    # If not, make a best guess based on the filename
    filename_lower = filename.lower()
    
    # Check for common indicators in the filename
    if any(kw in filename_lower for kw in ["resolution", "draft", "final resolution"]):
        return "resolution"
    elif any(kw in filename_lower for kw in ["speech", "speeches", "address", "statement"]):
        return "speech"
    elif any(kw in filename_lower for kw in ["position paper", "position", "policy paper", "_position_"]):
        return "position_paper"
    
    # Default to position paper if we can't determine
    print(f"Warning: Could not determine document type for {filename}. Defaulting to position_paper.")
    return "position_paper"

def train_model(training_data, epochs=3, batch_size=8):
    """
    Train the document type classifier.
    
    Args:
        training_data (list): List of (text, label) tuples
        epochs (int): Number of training epochs
        batch_size (int): Batch size for training
    
    Returns:
        tuple: (classifier, metrics)
    """
    # Split texts and labels
    texts = [item[0] for item in training_data]
    labels = [item[1] for item in training_data]
    
    # Print distribution
    label_counts = {}
    for label in labels:
        label_counts[label] = label_counts.get(label, 0) + 1
    
    print("\nTraining data distribution:")
    for label, count in label_counts.items():
        print(f"{DOCUMENT_TYPES[label]}: {count} examples ({count/len(labels)*100:.1f}%)")
    
    # Initialize the classifier
    classifier = DocumentTypeClassifier()
    
    # Set up training arguments
    training_args = TrainingArguments(
        output_dir="./models/document-type-classifier",
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size,
        weight_decay=0.01,
        logging_dir="./logs",
        evaluation_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
    )
    
    # Train the model
    print("\nStarting training...")
    try:
        metrics = classifier.finetune(texts, labels, epochs=epochs, batch_size=batch_size)
        print(f"Training completed with metrics: {metrics}")
    except Exception as e:
        print(f"Error during training: {e}")
        import traceback
        traceback.print_exc()
        return classifier, None
    
    return classifier, metrics

def process_test_pdf(classifier, pdf_path, output_dir=None):
    """
    Process a test PDF file and classify it.
    
    Args:
        classifier (DocumentTypeClassifier): Trained classifier
        pdf_path (str): Path to the PDF file
        output_dir (str, optional): Directory to save results
    
    Returns:
        dict: Classification results
    """
    from pdf_json import convert_pdf_to_json
    
    # Extract file name
    file_name = os.path.basename(pdf_path)
    
    # Generate output JSON path
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        json_path = os.path.join(output_dir, os.path.splitext(file_name)[0] + '_result.json')
    else:
        json_path = os.path.splitext(pdf_path)[0] + '_result.json'
    
    # Convert PDF to JSON
    print(f"Converting {file_name} to JSON...")
    json_str = convert_pdf_to_json(pdf_path, multi_topic=False, manual_segmentation=False)
    data = json.loads(json_str)
    
    # Extract text
    text = data.get('content', {}).get('main', '')
    
    # Classify document
    print(f"Classifying {file_name}...")
    doc_type, confidence = classifier.predict(text, document_name=file_name)
    
    # Create result
    result = {
        "document_name": file_name,
        "classification": {
            "document_type": doc_type,
            "confidence": confidence
        }
    }
    
    # Save result
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=4)
    
    return result

def test_model(classifier, test_dir, output_dir=None):
    """
    Test the model on PDF files in a directory.
    
    Args:
        classifier (DocumentTypeClassifier): Trained classifier
        test_dir (str): Directory containing test PDF files
        output_dir (str, optional): Directory to save results
    
    Returns:
        list: List of classification results
    """
    # Get all PDF files in the directory
    pdf_files = [f for f in os.listdir(test_dir) if f.lower().endswith('.pdf')]
    
    if not pdf_files:
        print(f"No PDF files found in {test_dir}")
        return []
    
    print(f"Found {len(pdf_files)} PDF files for testing")
    
    results = []
    
    for pdf_file in tqdm(pdf_files, desc="Testing PDFs"):
        pdf_path = os.path.join(test_dir, pdf_file)
        result = process_test_pdf(classifier, pdf_path, output_dir)
        results.append(result)
    
    return results

def main():
    parser = argparse.ArgumentParser(description='Train and test document type classifier')
    parser.add_argument('--processed_dir', type=str, default='./papers/processed',
                        help='Directory containing processed JSON files')
    parser.add_argument('--test_dir', type=str, default='./papers/testing',
                        help='Directory containing test PDF files')
    parser.add_argument('--output_dir', type=str, default='./models/document-type-classifier',
                        help='Directory to save trained model and results')
    parser.add_argument('--epochs', type=int, default=3, help='Number of training epochs')
    parser.add_argument('--batch_size', type=int, default=4, help='Batch size for training')
    args = parser.parse_args()
    
    # Make paths relative to the script directory
    processed_dir = args.processed_dir
    if not os.path.isabs(processed_dir):
        processed_dir = os.path.join(current_dir, processed_dir)
    
    test_dir = args.test_dir
    if not os.path.isabs(test_dir):
        test_dir = os.path.join(current_dir, test_dir)
    
    output_dir = args.output_dir
    if not os.path.isabs(output_dir):
        output_dir = os.path.join(current_dir, output_dir)
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Load processed JSON data
    training_data = load_processed_json_data(processed_dir)
    
    if not training_data:
        print("No training data available. Please make sure there are processed JSON files.")
        return
    
    # Train the model
    classifier, metrics = train_model(training_data, epochs=args.epochs, batch_size=args.batch_size)
    
    # Test the model on test PDFs
    if os.path.exists(test_dir):
        test_results_dir = os.path.join(output_dir, "test_results")
        os.makedirs(test_results_dir, exist_ok=True)
        
        results = test_model(classifier, test_dir, test_results_dir)
        
        # Print summary
        print("\nTest Results Summary:")
        for result in results:
            doc_name = result["document_name"]
            doc_type = result["classification"]["document_type"]
            confidence = result["classification"]["confidence"]
            print(f"{doc_name}: {doc_type} (confidence: {confidence:.2f})")
    else:
        print(f"Test directory {test_dir} not found. Skipping testing.")
    
    print(f"\nModel saved to {output_dir}")

if __name__ == "__main__":
    main() 