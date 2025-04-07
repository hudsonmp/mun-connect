"""
Train the Topic Classifier with sample data or existing segmented PDFs.
This script can be re-run as more data becomes available to improve the classifier.
"""

import os
import json
import argparse
import numpy as np
from distilbert_classifier import TopicClassifier, prepare_training_data

def load_json_data(json_file):
    """
    Load segmented data from a JSON file.
    
    Args:
        json_file (str): Path to the JSON file
        
    Returns:
        list: List of (text, label) tuples for training
    """
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    training_data = []
    
    # Check if it's a multi-topic document
    if data.get('multi_topic', False):
        content = data.get('content', {})
        # Convert topic names to numerical labels
        topic_map = {topic_name: idx for idx, topic_name in enumerate(content.keys())}
        
        # Add each segment as a training example
        for topic_name, text in content.items():
            label = topic_map[topic_name]
            training_data.append((text, label))
    
    return training_data

def find_json_files(directory):
    """
    Find all JSON files in a directory.
    
    Args:
        directory (str): Directory to search
        
    Returns:
        list: List of JSON file paths
    """
    json_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.json'):
                json_files.append(os.path.join(root, file))
    return json_files

def create_example_data():
    """
    Create example training data for model training when real data is not available.
    This data represents common topics in UN committee documents.
    
    Returns:
        list: List of (text, label) tuples
    """
    example_data = [
        # Topic 0: Climate Change
        ("Climate change is a global emergency requiring immediate action from all nations. The effects of rising temperatures include sea level rise, extreme weather events, and loss of biodiversity.",
         0),
        ("The Paris Agreement provides a framework for nations to reduce greenhouse gas emissions and limit global warming to well below 2 degrees Celsius above pre-industrial levels.",
         0),
        ("Developing nations are disproportionately affected by climate change despite contributing less to global emissions. Climate finance is essential to support their adaptation efforts.",
         0),
        
        # Topic 1: Economic Development
        ("Sustainable economic development must balance growth with environmental protection and social inclusion. The UN Sustainable Development Goals provide a roadmap for this balance.",
         1),
        ("International trade policies should prioritize fair and equitable access to markets for developing nations. Trade barriers often disadvantage the most vulnerable economies.",
         1),
        ("Digital transformation is reshaping global economies, and closing the digital divide between developed and developing nations is crucial for inclusive economic growth.",
         1),
        
        # Topic 2: Human Rights
        ("All human beings are born free and equal in dignity and rights. The Universal Declaration of Human Rights enshrines these fundamental principles.",
         2),
        ("Freedom of expression and access to information are essential for democratic societies. Governments must protect these rights while combating harmful misinformation.",
         2),
        ("The rights of refugees and migrants must be protected, including their right to seek asylum from persecution. Host nations have responsibilities under international law.",
         2),
        
        # Topic 3: Peace and Security
        ("Nuclear disarmament remains an urgent priority for global security. The Non-Proliferation Treaty provides a framework for reducing nuclear arsenals.",
         3),
        ("Conflict prevention requires addressing root causes including poverty, inequality, and environmental degradation. Early warning systems and preventive diplomacy are essential tools.",
         3),
        ("Peacekeeping operations must respect national sovereignty while fulfilling their mandate to protect civilians. Local ownership of peace processes increases their effectiveness.",
         3),
        
        # Topic 4: Public Health
        ("Universal health coverage is a fundamental goal to ensure all people have access to essential health services without financial hardship.",
         4),
        ("Pandemic preparedness requires global cooperation in surveillance, research, and equitable distribution of vaccines and treatments.",
         4),
        ("Antimicrobial resistance threatens to undermine decades of progress in medicine and requires coordinated action across human health, animal health, and environmental sectors.",
         4)
    ]
    
    return example_data

def main():
    parser = argparse.ArgumentParser(description='Train the topic classifier')
    parser.add_argument('--data_dir', type=str, help='Directory containing segmented JSON files')
    parser.add_argument('--epochs', type=int, default=3, help='Number of training epochs')
    parser.add_argument('--use_example_data', action='store_true', help='Use example data for training')
    args = parser.parse_args()
    
    training_data = []
    
    # Load real data if available
    if args.data_dir and os.path.exists(args.data_dir):
        json_files = find_json_files(args.data_dir)
        print(f"Found {len(json_files)} JSON files for training")
        
        for json_file in json_files:
            file_data = load_json_data(json_file)
            if file_data:
                training_data.extend(file_data)
                
    # Add example data if specified or if no real data is available
    if args.use_example_data or not training_data:
        example_data = create_example_data()
        training_data.extend(example_data)
        print("Using example data for training")
    
    if not training_data:
        print("No training data available. Please provide segmented JSON files or use example data.")
        return
    
    # Prepare training data
    print(f"Preparing training data with {len(training_data)} examples")
    train_texts, train_labels = prepare_training_data(training_data)
    
    # Initialize the classifier
    num_labels = len(set(train_labels))
    print(f"Training classifier with {num_labels} topic labels")
    classifier = TopicClassifier(num_labels=num_labels)
    
    # Train the model
    print("Starting training...")
    metrics = classifier.finetune(train_texts, train_labels, epochs=args.epochs)
    
    print(f"Training completed with metrics: {metrics}")
    print("Model saved to ./models/topic-classifier")

if __name__ == "__main__":
    main() 