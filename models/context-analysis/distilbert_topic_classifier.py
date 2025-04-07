"""
DistilBERT Classifier Base Class - Used for both Topic Classification and Document Type Classification.
This module provides the base functionality for fine-tuning DistilBERT models on custom classification tasks.
"""

import os
import torch
import numpy as np
from transformers import (
    DistilBertTokenizer, 
    DistilBertForSequenceClassification,
    TrainingArguments, 
    Trainer
)
from sklearn.model_selection import train_test_split
from torch.utils.data import Dataset

class TextClassificationDataset(Dataset):
    """Dataset for text classification tasks."""
    
    def __init__(self, encodings, labels):
        self.encodings = encodings
        self.labels = labels

    def __getitem__(self, idx):
        item = {key: torch.tensor(val[idx]) for key, val in self.encodings.items()}
        item['labels'] = torch.tensor(self.labels[idx])
        return item

    def __len__(self):
        return len(self.labels)

def prepare_training_data(data):
    """
    Convert a list of (text, label) tuples into separate lists of texts and labels.
    
    Args:
        data (list): List of (text, label) tuples
        
    Returns:
        tuple: (list of texts, list of labels)
    """
    texts = [item[0] for item in data]
    labels = [item[1] for item in data]
    return texts, labels

class TopicClassifier:
    """Topic classification using DistilBERT."""
    
    def __init__(self, num_labels=5, model_name="distilbert-base-uncased"):
        """
        Initialize the classifier.
        
        Args:
            num_labels (int): Number of topic labels
            model_name (str): Pre-trained model name
        """
        self.num_labels = num_labels
        self.model_name = model_name
        self.tokenizer = DistilBertTokenizer.from_pretrained(model_name)
        self.model = DistilBertForSequenceClassification.from_pretrained(
            model_name, num_labels=num_labels
        )
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        
    def tokenize_data(self, texts):
        """
        Tokenize input texts.
        
        Args:
            texts (list): List of text strings
            
        Returns:
            dict: Tokenized inputs
        """
        return self.tokenizer(
            texts,
            padding="max_length",
            truncation=True,
            max_length=512,
            return_tensors="pt"
        )
    
    def finetune(self, train_texts, train_labels, epochs=3, batch_size=8):
        """
        Fine-tune the model on training data.
        
        Args:
            train_texts (list): List of training text strings
            train_labels (list): List of training labels
            epochs (int): Number of training epochs
            batch_size (int): Batch size for training
            
        Returns:
            dict: Training metrics
        """
        # Split into train and validation sets
        train_texts, val_texts, train_labels, val_labels = train_test_split(
            train_texts, train_labels, test_size=0.2
        )
        
        # Tokenize data
        train_encodings = self.tokenize_data(train_texts)
        val_encodings = self.tokenize_data(val_texts)
        
        # Create datasets
        train_dataset = TextClassificationDataset(train_encodings, train_labels)
        val_dataset = TextClassificationDataset(val_encodings, val_labels)
        
        # Set up training arguments
        training_args = TrainingArguments(
            output_dir="./models/topic-classifier",
            num_train_epochs=epochs,
            per_device_train_batch_size=batch_size,
            per_device_eval_batch_size=batch_size,
            warmup_steps=500,
            weight_decay=0.01,
            logging_dir="./logs",
            logging_steps=10,
            evaluation_strategy="epoch",
            save_strategy="epoch",
            load_best_model_at_end=True,
        )
        
        # Initialize trainer
        trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=val_dataset
        )
        
        # Train the model
        trainer.train()
        
        # Save the model
        self.model.save_pretrained("./models/topic-classifier")
        self.tokenizer.save_pretrained("./models/topic-classifier")
        
        # Evaluate the model
        metrics = trainer.evaluate()
        
        return metrics
    
    def predict(self, text):
        """
        Predict the topic of a text.
        
        Args:
            text (str): Input text
            
        Returns:
            int: Predicted topic label
        """
        # Tokenize input text
        inputs = self.tokenizer(
            text,
            padding="max_length",
            truncation=True,
            max_length=512,
            return_tensors="pt"
        )
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        # Make prediction
        with torch.no_grad():
            outputs = self.model(**inputs)
            predictions = outputs.logits.argmax(dim=-1)
        
        return predictions.item()
    
    def load_model(self, model_path):
        """
        Load a pre-trained model.
        
        Args:
            model_path (str): Path to the model directory
        """
        self.model = DistilBertForSequenceClassification.from_pretrained(model_path)
        self.tokenizer = DistilBertTokenizer.from_pretrained(model_path)
        self.model.to(self.device)
    
    def segment_text(self, text, max_segment_length=1000, overlap=200):
        """
        Segment text into chunks and classify each chunk.
        
        Args:
            text (str): Input text
            max_segment_length (int): Maximum length of each segment
            overlap (int): Overlap between segments
            
        Returns:
            dict: Dictionary with topic names as keys and their content as values
        """
        # Split text into paragraphs
        paragraphs = text.split('\n\n')
        
        # Initialize segments
        segments = [""]
        current_segment = 0
        
        # Distribute paragraphs into segments
        for paragraph in paragraphs:
            # If adding this paragraph would exceed max_segment_length,
            # start a new segment (with overlap)
            if len(segments[current_segment]) + len(paragraph) > max_segment_length:
                # Get the last part of the current segment for overlap
                last_part = segments[current_segment][-overlap:]
                current_segment += 1
                segments.append(last_part)
            
            # Add paragraph to current segment
            segments[current_segment] += paragraph + "\n\n"
        
        # Classify each segment
        segment_topics = {}
        for i, segment in enumerate(segments):
            topic = self.predict(segment)
            segment_name = f"Topic {topic}"
            
            # Add to existing topic or create new
            if segment_name in segment_topics:
                segment_topics[segment_name] += segment
            else:
                segment_topics[segment_name] = segment
        
        return segment_topics 