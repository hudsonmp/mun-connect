"""
Train the Document Type Classifier from processed JSON files.
This script loads the JSON files from the processed directory and uses them to train the model.
"""

import os
import json
import argparse
import torch
import numpy as np
from tqdm import tqdm
import sys

# Add the current directory to Python path to find the modules
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# Import our DocumentTypeClassifier
from distilbert_document_type_classifier import DocumentTypeClassifier, DOCUMENT_TYPES

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
            
            # Get document type if it exists in the JSON
            doc_type = data.get('document_type')
            
            # If document type not defined in JSON, try to determine from filename
            if not doc_type:
                # Default to analyzing content
                print(f"\nDocument type not found in {json_file}. Let's determine it:")
                doc_type = determine_document_type_interactive(json_file, data)
                
                # Save the document type back to the JSON
                data['document_type'] = doc_type
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=4)
            
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

def determine_document_type_interactive(filename, data):
    """
    Interactively determine document type.
    
    Args:
        filename (str): Name of the file
        data (dict): JSON data
    
    Returns:
        str: Document type
    """
    # Try to get sample text
    if data.get('multi_topic', False):
        # Get the first topic's text
        content = data.get('content', {})
        text = next(iter(content.values()), "")
    else:
        text = data.get('content', {}).get('main', "")
    
    # Show preview
    preview = text[:200] + "..." if len(text) > 200 else text
    print(f"\nDocument: {filename}")
    print(f"Preview: {preview}\n")
    
    # Show options
    print("Document types:")
    for idx, doc_type in DOCUMENT_TYPES.items():
        print(f"{idx}: {doc_type}")
    
    # Get user input
    while True:
        try:
            label = int(input("Enter document type number: "))
            if label in DOCUMENT_TYPES:
                return DOCUMENT_TYPES[label]
            print(f"Invalid input. Please enter a number between 0-{len(DOCUMENT_TYPES)-1}")
        except ValueError:
            print("Please enter a valid number.")
        except KeyboardInterrupt:
            print("\nClassification interrupted. Using default classification (position_paper).")
            return "position_paper"

def train_model(training_data, epochs=5, batch_size=8):
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

def validate_model(classifier, test_data, output_file=None):
    """
    Validate the trained model on test data.
    
    Args:
        classifier (DocumentTypeClassifier): Trained classifier
        test_data (list): List of (text, label) tuples for testing
        output_file (str, optional): File to save results
    
    Returns:
        float: Accuracy
    """
    if not test_data:
        print("No test data provided for validation.")
        return 0.0
    
    results = []
    correct = 0
    
    print("\nValidating model...")
    for text, true_label in tqdm(test_data, desc="Validating"):
        try:
            # Predict document type
            predicted_type, confidence = classifier.predict(text)
            
            # Convert document type string to index
            doc_type_to_idx = {doc_type: idx for idx, doc_type in DOCUMENT_TYPES.items()}
            predicted_label = doc_type_to_idx.get(predicted_type, -1)
            
            # Check if prediction is correct
            is_correct = predicted_label == true_label
            if is_correct:
                correct += 1
            
            # Add result
            results.append({
                'text_preview': text[:100] + "..." if len(text) > 100 else text,
                'true_label': DOCUMENT_TYPES[true_label],
                'predicted_label': predicted_type,
                'confidence': confidence,
                'is_correct': is_correct
            })
        except Exception as e:
            print(f"Error predicting document type: {e}")
    
    # Calculate accuracy
    accuracy = correct / len(test_data) if test_data else 0.0
    print(f"\nValidation accuracy: {accuracy:.2%}")
    
    # Save results
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'accuracy': accuracy,
                'results': results
            }, f, indent=4)
    
    return accuracy

def main():
    parser = argparse.ArgumentParser(description='Train the document type classifier from processed JSON files')
    parser.add_argument('--processed_dir', type=str, default='./papers/processed',
                        help='Directory containing processed JSON files')
    parser.add_argument('--output_dir', type=str, default='./models/document-type-classifier',
                        help='Directory to save the trained model')
    parser.add_argument('--epochs', type=int, default=5, help='Number of training epochs')
    parser.add_argument('--batch_size', type=int, default=8, help='Batch size for training')
    parser.add_argument('--use_example_data', action='store_true', 
                        help='Use example data for training')
    parser.add_argument('--test_split', type=float, default=0.2,
                        help='Fraction of data to use for testing (default: 0.2)')
    parser.add_argument('--results_file', type=str, default='validation_results.json',
                        help='File to save validation results')
    args = parser.parse_args()
    
    # Make processed_dir relative to the script directory
    processed_dir = args.processed_dir
    if not os.path.isabs(processed_dir):
        processed_dir = os.path.join(current_dir, processed_dir)
    
    # Ensure output directory exists
    os.makedirs(args.output_dir, exist_ok=True)
    
    training_data = []
    
    # Add example data if specified
    if args.use_example_data:
        example_data = create_initial_training_data()
        training_data.extend(example_data)
        print(f"Using {len(example_data)} example documents for training")
    
    # Load processed JSON data
    if processed_dir and os.path.exists(processed_dir):
        processed_data = load_processed_json_data(processed_dir)
        training_data.extend(processed_data)
        print(f"Loaded {len(processed_data)} documents from processed JSON files")
    
    if not training_data:
        print("No training data available. Please provide processed JSON files or use example data.")
        return
    
    # Split into training and test sets
    np.random.shuffle(training_data)
    test_size = int(len(training_data) * args.test_split)
    test_data = training_data[:test_size]
    train_data = training_data[test_size:]
    
    print(f"Split data into {len(train_data)} training and {len(test_data)} test examples")
    
    # Train the model
    classifier, metrics = train_model(train_data, epochs=args.epochs, batch_size=args.batch_size)
    
    # Validate the model
    results_file = args.results_file
    if not os.path.isabs(results_file):
        results_file = os.path.join(args.output_dir, results_file)
    
    accuracy = validate_model(classifier, test_data, results_file)
    
    # Check if accuracy meets threshold
    if accuracy >= 0.8:
        print(f"\nSuccess! Model achieved {accuracy:.2%} accuracy, which meets the 80% threshold.")
    else:
        print(f"\nWarning: Model achieved {accuracy:.2%} accuracy, which is below the 80% threshold.")
        print("Consider adding more training data or adjusting training parameters.")
    
    print(f"Model saved to {args.output_dir}")
    print(f"Validation results saved to {results_file}")

if __name__ == "__main__":
    main() 