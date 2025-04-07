"""
Test the document type classifier model on the processed documents.
This script loads all the JSON files from the processed directory and tests the model's accuracy.
"""

import os
import json
import argparse
import sys
from tqdm import tqdm

# Add the current directory to Python path to find the modules
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# Import our DocumentTypeClassifier
from distilbert_document_type_classifier import DocumentTypeClassifier, DOCUMENT_TYPES

def load_and_test_processed_data(processed_dir, classifier, output_file):
    """
    Load data from processed JSON files and test the model on them.
    
    Args:
        processed_dir (str): Directory containing processed JSON files
        classifier (DocumentTypeClassifier): Trained classifier
        output_file (str): File to save results
    
    Returns:
        dict: Testing results with accuracy
    """
    # Get all JSON files in the directory
    json_files = [f for f in os.listdir(processed_dir) if f.lower().endswith('.json')]
    print(f"Found {len(json_files)} JSON files for testing")
    
    doc_type_to_idx = {doc_type: idx for idx, doc_type in DOCUMENT_TYPES.items()}
    results = {
        "total_documents": len(json_files),
        "correct_predictions": 0,
        "document_types": {
            "resolution": {"total": 0, "correct": 0},
            "speech": {"total": 0, "correct": 0},
            "position_paper": {"total": 0, "correct": 0}
        },
        "detailed_results": []
    }
    
    for json_file in tqdm(json_files, desc="Testing documents"):
        file_path = os.path.join(processed_dir, json_file)
        
        try:
            # Load JSON
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Get document type if it exists in the JSON
            true_doc_type = data.get('document_type')
            if not true_doc_type:
                print(f"Warning: No document type found in {json_file}, skipping.")
                continue
            
            # Get the text to classify
            if data.get('multi_topic', False):
                # Use the first topic's text
                content = data.get('content', {})
                if not content:
                    print(f"Warning: No content found in {json_file}, skipping.")
                    continue
                text = next(iter(content.values()), "")
            else:
                text = data.get('content', {}).get('main', "")
            
            if not text.strip():
                print(f"Warning: Empty text in {json_file}, skipping.")
                continue
            
            # Track document type stats
            if true_doc_type in results["document_types"]:
                results["document_types"][true_doc_type]["total"] += 1
            
            # Predict using the model
            predicted_doc_type, confidence = classifier.predict(text, json_file)
            
            # Check if prediction is correct
            is_correct = predicted_doc_type == true_doc_type
            
            # Track results
            if is_correct:
                results["correct_predictions"] += 1
                if true_doc_type in results["document_types"]:
                    results["document_types"][true_doc_type]["correct"] += 1
            
            # Add detailed result
            results["detailed_results"].append({
                "file": json_file,
                "true_type": true_doc_type,
                "predicted_type": predicted_doc_type,
                "confidence": confidence,
                "is_correct": is_correct
            })
            
        except Exception as e:
            print(f"Error processing {json_file}: {e}")
    
    # Calculate accuracy
    if results["total_documents"] > 0:
        results["accuracy"] = results["correct_predictions"] / results["total_documents"]
    else:
        results["accuracy"] = 0
    
    # Calculate per-type accuracy
    for doc_type in results["document_types"]:
        if results["document_types"][doc_type]["total"] > 0:
            results["document_types"][doc_type]["accuracy"] = (
                results["document_types"][doc_type]["correct"] / 
                results["document_types"][doc_type]["total"]
            )
        else:
            results["document_types"][doc_type]["accuracy"] = 0
    
    # Save results
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=4)
    
    return results

def main():
    parser = argparse.ArgumentParser(description='Test the document type classifier on processed documents')
    parser.add_argument('--processed_dir', type=str, default='./papers/processed',
                        help='Directory containing processed JSON files')
    parser.add_argument('--model_dir', type=str, default='./models/document-type-classifier',
                        help='Directory containing the trained model')
    parser.add_argument('--output_file', type=str, default='./test_results.json',
                        help='File to save test results')
    args = parser.parse_args()
    
    # Make processed_dir relative to the script directory
    processed_dir = args.processed_dir
    if not os.path.isabs(processed_dir):
        processed_dir = os.path.join(current_dir, processed_dir)
    
    # Make model_dir relative to the script directory
    model_dir = args.model_dir
    if not os.path.isabs(model_dir):
        model_dir = os.path.join(current_dir, model_dir)
    
    # Initialize the classifier
    try:
        print(f"Loading model from {model_dir}")
        classifier = DocumentTypeClassifier(model_path=model_dir)
        print("Model loaded successfully")
    except Exception as e:
        print(f"Error loading model: {e}")
        # Fall back to default model initialization
        print("Falling back to default model initialization")
        classifier = DocumentTypeClassifier()
    
    # Test the model
    results = load_and_test_processed_data(processed_dir, classifier, args.output_file)
    
    # Print results
    print("\nTest Results:")
    print(f"Total documents: {results['total_documents']}")
    print(f"Correct predictions: {results['correct_predictions']}")
    print(f"Overall accuracy: {results['accuracy']:.2%}")
    
    print("\nAccuracy by document type:")
    for doc_type, stats in results["document_types"].items():
        if stats["total"] > 0:
            print(f"{doc_type}: {stats['accuracy']:.2%} ({stats['correct']}/{stats['total']})")
        else:
            print(f"{doc_type}: N/A (0 documents)")
    
    print(f"\nDetailed results saved to {args.output_file}")

if __name__ == "__main__":
    main() 