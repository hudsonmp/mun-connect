"""
DistilBERT Document Type Classifier - Classifies PDFs as resolution, speech, or position paper.
This module also analyzes PDF titles first to attempt classification before analyzing the content.
"""

import os
import re
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
import nltk
from nltk.tokenize import sent_tokenize
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

# The three document types we're classifying
DOCUMENT_TYPES = {
    0: "resolution",
    1: "speech",
    2: "position_paper"
}

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

class DocumentTypeClassifier:
    """Document type classification using DistilBERT."""
    
    def __init__(self, model_path=None):
        """
        Initialize the classifier.
        
        Args:
            model_path (str, optional): Path to pre-trained model
        """
        self.num_labels = len(DOCUMENT_TYPES)
        self.model_name = "distilbert-base-uncased"
        self.tokenizer = DistilBertTokenizer.from_pretrained(self.model_name)
        
        if model_path and os.path.exists(model_path):
            # Load existing model
            self.model = DistilBertForSequenceClassification.from_pretrained(model_path)
            self.tokenizer = DistilBertTokenizer.from_pretrained(model_path)
        else:
            # Initialize new model
            self.model = DistilBertForSequenceClassification.from_pretrained(
                self.model_name, num_labels=self.num_labels
            )
        
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
    
    def analyze_title(self, title):
        """
        Analyze the document title to attempt classification.
        
        Args:
            title (str): Document title
            
        Returns:
            int or None: Document type index if identifiable from title, else None
        """
        title_lower = title.lower()
        
        # Check for common indicators in the title
        if any(kw in title_lower for kw in ["resolution", "draft resolution", "final resolution"]):
            return 0  # Resolution
        elif any(kw in title_lower for kw in ["speech", "speeches", "address", "statement"]):
            return 1  # Speech
        elif any(kw in title_lower for kw in ["position paper", "position", "policy paper"]):
            return 2  # Position paper
        
        # If title contains phrases like "delegate of [country]" it's likely a speech
        if re.search(r"delegate of|representative of|speech by", title_lower):
            return 1  # Speech
        
        # If title contains topic markers, it's likely a position paper
        if re.search(r"topic [a-z]|committee:|delegation of", title_lower):
            return 2  # Position paper
        
        return None  # Can't determine from title
    
    def analyze_content_structure(self, text):
        """
        Analyze content structure to get hints about document type.
        
        Args:
            text (str): Document text
            
        Returns:
            int or None: Document type index if identifiable from structure, else None
        """
        # Count sentences
        sentences = sent_tokenize(text)
        
        # Resolution pattern: numbered clauses, formal language
        if re.search(r"\d+\.\s+[A-Z][a-z]+", text) and re.search(r"(Decides|Urges|Calls upon|Requests)", text):
            return 0  # Resolution
            
        # Speech pattern: short paragraphs, first person pronouns, salutations
        first_person_count = len(re.findall(r'\b(I|we|our|my)\b', text.lower()))
        salutation = bool(re.search(r'(thank you|distinguished|delegates|chair|honor)', text.lower()))
        if salutation and first_person_count > 5 and len(sentences) < 50:
            return 1  # Speech
            
        # Position paper pattern: longer, formal, mentions delegation
        country_mention = bool(re.search(r'delegation of|position of|the .{3,30} delegation', text.lower()))
        if country_mention and len(sentences) > 40:
            return 2  # Position paper
            
        return None
    
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
        self.model.save_pretrained("./models/document-type-classifier")
        self.tokenizer.save_pretrained("./models/document-type-classifier")
        
        # Evaluate the model
        metrics = trainer.evaluate()
        
        return metrics
    
    def predict(self, text, document_name=None):
        """
        Predict the document type.
        
        Args:
            text (str): Input text
            document_name (str, optional): Document name for title analysis
            
        Returns:
            str: Document type ("resolution", "speech", or "position_paper")
            float: Confidence score
        """
        # First try to classify by document name
        doc_type_idx = None
        if document_name:
            doc_type_idx = self.analyze_title(document_name)
        
        # If title analysis inconclusive, try structure analysis
        if doc_type_idx is None:
            doc_type_idx = self.analyze_content_structure(text)
        
        # If both rule-based approaches fail, use the model
        if doc_type_idx is None:
            # Tokenize input text
            inputs = self.tokenizer(
                text[:1000],  # Use the first 1000 chars for faster processing
                padding="max_length",
                truncation=True,
                max_length=512,
                return_tensors="pt"
            )
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Make prediction
            with torch.no_grad():
                outputs = self.model(**inputs)
                probs = torch.nn.functional.softmax(outputs.logits, dim=-1)
                prediction = outputs.logits.argmax(dim=-1).item()
                confidence = probs[0][prediction].item()
            
            doc_type_idx = prediction
        else:
            # If rule-based approach succeeds, set high confidence
            confidence = 0.95
        
        return DOCUMENT_TYPES[doc_type_idx], confidence
    
    def save_model(self, model_path="./models/document-type-classifier"):
        """
        Save the model to a directory.
        
        Args:
            model_path (str): Directory to save the model
        """
        os.makedirs(model_path, exist_ok=True)
        self.model.save_pretrained(model_path)
        self.tokenizer.save_pretrained(model_path)
    
    def load_model(self, model_path):
        """
        Load a pre-trained model.
        
        Args:
            model_path (str): Path to the model directory
        """
        self.model = DistilBertForSequenceClassification.from_pretrained(model_path)
        self.tokenizer = DistilBertTokenizer.from_pretrained(model_path)
        self.model.to(self.device)

# Example usage
if __name__ == "__main__":
    # Initialize classifier
    classifier = DocumentTypeClassifier()
    
    # Example text snippets
    resolution_text = """DRAFT RESOLUTION 
    The General Assembly,
    Recalling its resolution 1/1 of 25 June 2006,
    Deeply concerned about the ongoing situation,
    1. Decides to establish a commission of inquiry;
    2. Urges all parties to cooperate fully;
    3. Requests the Secretary-General to report on implementation;"""
    
    speech_text = """Thank you, Madam Chair.
    Distinguished delegates, it is my honor to address this committee today.
    My delegation believes that this issue requires our immediate attention.
    We propose a three-part solution that addresses the root causes.
    I thank you for your attention."""
    
    position_paper_text = """POSITION PAPER
    Delegation of France
    Committee: Security Council
    Topic A: Situation in the Middle East
    
    The French Republic recognizes the complexity of the situation in the Middle East.
    Our position is based on the following principles: sovereignty, dialogue, and multilateralism.
    France proposes the following solutions:
    1. Enhanced regional dialogue
    2. Economic development initiatives
    3. Security cooperation mechanisms"""
    
    # Predict document types
    for text, name in [
        (resolution_text, "Draft Resolution.pdf"),
        (speech_text, "Delegate Speech.pdf"),
        (position_paper_text, "France Position Paper.pdf")
    ]:
        doc_type, confidence = classifier.predict(text, name)
        print(f"Document '{name}' classified as: {doc_type} (confidence: {confidence:.2f})")