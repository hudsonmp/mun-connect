#!/usr/bin/env python
"""
Debug script for testing the document classifier model.
This script runs a simplified version of the model training and testing.
"""

import sys
import os
import torch
from train_model_pytorch import (
    create_example_training_data, 
    DOC_TYPE_TO_IDX, 
    TextClassificationDataset,
    train_model,
    test_model
)

# Enable flush of print statements
class Unbuffered:
    def __init__(self, stream):
        self.stream = stream
    def write(self, data):
        self.stream.write(data)
        self.stream.flush()
    def writelines(self, datas):
        self.stream.writelines(datas)
        self.stream.flush()
    def __getattr__(self, attr):
        return getattr(self.stream, attr)

sys.stdout = Unbuffered(sys.stdout)

def main():
    print("Running debug mode")
    
    # Create example data
    examples = create_example_training_data()
    print(f"Created {len(examples)} example documents")
    
    # Prepare data
    texts = [doc["content"] for doc in examples]
    labels = [DOC_TYPE_TO_IDX[doc["document_type"]] for doc in examples]
    
    # Split data
    train_texts, test_texts, train_labels, test_labels = texts[:2], texts[2:], labels[:2], labels[2:]
    
    # Create datasets
    print("Creating datasets...")
    train_dataset = TextClassificationDataset(train_texts, train_labels)
    test_dataset = TextClassificationDataset(test_texts, test_labels, vocab=train_dataset.vocab)
    
    # Train
    device = torch.device("cpu")
    print("Training model with 1 epoch...")
    model = train_model(
        train_dataset, 
        test_dataset,
        vocab_size=len(train_dataset.vocab),
        batch_size=1,
        epochs=1
    )
    
    # Test
    print("Testing model...")
    test_model(test_dataset, model, device)
    
    print("Debug run completed")

if __name__ == "__main__":
    main() 