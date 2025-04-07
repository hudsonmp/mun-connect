#!/usr/bin/env python
"""
Train and test a document classifier using PyTorch.
This script trains a simple LSTM model to classify documents by type.
"""

import os
import json
import argparse
import random
import numpy as np
from typing import List, Dict, Tuple, Optional, Any
from sklearn.model_selection import train_test_split
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from collections import Counter

# Document type to index mapping
DOC_TYPE_TO_IDX = {
    "resolution": 0,
    "speech": 1,
    "position_paper": 2
}

IDX_TO_DOC_TYPE = {v: k for k, v in DOC_TYPE_TO_IDX.items()}

class TextClassificationDataset(Dataset):
    """Dataset for text classification tasks"""
    
    def __init__(self, texts, labels, vocab=None, max_length=512):
        self.texts = texts
        self.labels = labels
        self.max_length = max_length
        
        # Build vocabulary if not provided
        if vocab is None:
            self.build_vocab(texts)
        else:
            self.vocab = vocab
            
        # Convert texts to indices
        self.text_indices = [self.text_to_indices(text) for text in texts]
        
    def build_vocab(self, texts):
        """Build vocabulary from texts"""
        all_words = []
        for text in texts:
            all_words.extend(text.lower().split())
        
        # Count words and select top 10000
        word_counts = Counter(all_words)
        self.vocab = {"<PAD>": 0, "<UNK>": 1}
        for word, _ in word_counts.most_common(9998):  # Leave room for PAD and UNK
            self.vocab[word] = len(self.vocab)
            
    def text_to_indices(self, text):
        """Convert a text to a list of indices"""
        words = text.lower().split()
        indices = [self.vocab.get(word, self.vocab["<UNK>"]) for word in words[:self.max_length]]
        
        # Pad if necessary
        if len(indices) < self.max_length:
            indices += [self.vocab["<PAD>"]] * (self.max_length - len(indices))
            
        return indices
    
    def __len__(self):
        return len(self.texts)
    
    def __getitem__(self, idx):
        return {
            "text": torch.tensor(self.text_indices[idx], dtype=torch.long),
            "label": torch.tensor(self.labels[idx], dtype=torch.long)
        }

class SimpleClassifier(nn.Module):
    """A simple text classifier using embeddings and LSTM"""
    
    def __init__(self, vocab_size, embedding_dim, hidden_dim, num_classes):
        super(SimpleClassifier, self).__init__()
        self.embedding = nn.Embedding(vocab_size, embedding_dim, padding_idx=0)
        self.lstm = nn.LSTM(embedding_dim, hidden_dim, batch_first=True)
        self.fc = nn.Linear(hidden_dim, num_classes)
        self.dropout = nn.Dropout(0.3)
        
    def forward(self, x):
        # x shape: (batch_size, seq_length)
        embedded = self.embedding(x)  # (batch_size, seq_length, embedding_dim)
        lstm_out, _ = self.lstm(embedded)  # (batch_size, seq_length, hidden_dim)
        
        # Take the last non-padded output from LSTM
        last_out = lstm_out[:, -1, :]  # (batch_size, hidden_dim)
        
        out = self.dropout(last_out)
        out = self.fc(out)  # (batch_size, num_classes)
        return out

def load_processed_data(processed_dir: str) -> List[Dict]:
    """Load processed data from JSON files"""
    data = []
    for file_name in os.listdir(processed_dir):
        if file_name.endswith(".json"):
            file_path = os.path.join(processed_dir, file_name)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    doc = json.load(f)
                    # Make sure document has content and document_type
                    if "content" in doc and "document_type" in doc:
                        data.append(doc)
                    else:
                        print(f"Warning: Missing required fields in {file_path}")
            except Exception as e:
                print(f"Error reading {file_path}: {e}")
    return data

def create_example_training_data():
    """Create example training data for each document type"""
    examples = [
        {
            "document_type": "resolution",
            "content": "The Economic and Social Council, Recalling its resolution 2019/14 of 7 June 2019, "
                     "Recognizing the need for a comprehensive and coordinated approach to addressing the "
                     "global economic crisis caused by the COVID-19 pandemic, Emphasizing the importance of "
                     "international cooperation and solidarity in responding to the challenges posed by the "
                     "pandemic, 1. Calls upon all Member States to strengthen their cooperation in addressing "
                     "the economic and social impacts of the pandemic; 2. Requests the Secretary-General to "
                     "submit a report on this matter to the Economic and Social Council at its 2023 session;"
        },
        {
            "document_type": "speech",
            "content": "Mr. President, distinguished delegates, I stand before you today representing "
                     "my country in these challenging times. The issues we face are complex and require "
                     "our immediate attention. Climate change continues to threaten our planet, economic "
                     "inequality persists, and conflicts arise in various regions. We must work together "
                     "to address these challenges. My delegation proposes a three-point plan to tackle "
                     "these issues. First, we must increase funding for renewable energy initiatives. "
                     "Second, we should establish a more equitable trade system. Third, we need to strengthen "
                     "peacekeeping operations in conflict zones. Thank you for your attention."
        },
        {
            "document_type": "position_paper",
            "content": "Position Paper: The Delegation of France on the Topic of Climate Change "
                     "I. Introduction "
                     "France acknowledges climate change as one of the most pressing issues of our time. "
                     "We remain committed to the Paris Agreement and have implemented numerous policies to "
                     "reduce our carbon emissions by 40y 2030. "
                     "II. Past International Actions "
                     "France has been a leading advocate for international climate action, hosting the COP21 "
                     "in 2015 which resulted in the landmark Paris Agreement. We have contributed €5 billion "
                     "annually to the Green Climate Fund and have supported climate initiatives in developing nations. "
                     "III. Proposed Solutions "
                     "1. We propose establishing a universal carbon pricing mechanism. "
                     "2. We call for increased investments in renewable energy technologies. "
                     "3. We support enhanced adaptation measures for vulnerable nations. "
                     "IV. Conclusion "
                     "France stands ready to collaborate with all nations to address this global challenge. "
                     "The time for action is now, and together we can create a sustainable future for generations to come."
        }
    ]
    return examples

def train_model(train_dataset, val_dataset, vocab_size, embedding_dim=100, hidden_dim=128, 
                num_classes=3, batch_size=8, epochs=5, lr=0.001):
    """Train the document type classifier"""
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")
    
    # Create data loaders
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size)
    
    # Initialize model
    model = SimpleClassifier(vocab_size, embedding_dim, hidden_dim, num_classes)
    model.to(device)
    
    # Loss function and optimizer
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=lr)
    
    # Training loop
    for epoch in range(epochs):
        model.train()
        total_loss = 0
        
        for batch in train_loader:
            inputs = batch["text"].to(device)
            labels = batch["label"].to(device)
            
            # Forward pass
            outputs = model(inputs)
            loss = criterion(outputs, labels)
            
            # Backward pass and optimize
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item()

def test_model(test_dataset, model, device, output_file=None):
    """Test the trained model on test data"""
    test_loader = DataLoader(test_dataset, batch_size=16)
    
    model.eval()
    correct = 0
    total = 0
    all_predictions = []
    all_labels = []
    
    with torch.no_grad():
        for batch in test_loader:
            inputs = batch["text"].to(device)
            labels = batch["label"].to(device)
            
            outputs = model(inputs)
            _, predicted = torch.max(outputs, 1)
            
            total += labels.size(0)
            correct += (predicted == labels).sum().item()
            
            all_predictions.extend(predicted.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())
    
    accuracy = correct / total
    print(f"Test Accuracy: {accuracy:.4f}")
    
    # Save results if output file is provided
    if output_file:
        results = {
            "accuracy": accuracy,
            "predictions": [IDX_TO_DOC_TYPE[p] for p in all_predictions],
            "true_labels": [IDX_TO_DOC_TYPE[l] for l in all_labels]
        }
        with open(output_file, "w") as f:
            json.dump(results, f, indent=4)
    
    return accuracy
def main():
    parser = argparse.ArgumentParser(description="Train and test a document classifier")
    parser.add_argument("--processed_dir", default="./papers/processed", help="Directory with processed JSON files")
    parser.add_argument("--output_dir", default="./model", help="Directory to save model and results")
    parser.add_argument("--epochs", type=int, default=5, help="Number of training epochs")
    parser.add_argument("--batch_size", type=int, default=8, help="Batch size for training")
    parser.add_argument("--use_example_data", action="store_true", help="Use example data instead of loading from files")
