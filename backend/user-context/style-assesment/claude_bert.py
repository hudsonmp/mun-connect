from transformers import BertModel, BertTokenizer
import torch
import numpy as np

class BERTStyleFeatureExtractor:
    def __init__(self):
        # Load pre-trained BERT
        self.tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')
        self.model = BertModel.from_pretrained('bert-base-uncased')
        self.model.eval()  # Set to evaluation mode
        
    def extract_features(self, text):
        """Extract style features from text using BERT"""
        # Tokenize and prepare for BERT
        inputs = self.tokenizer(text, return_tensors="pt", 
                               padding=True, truncation=True, 
                               max_length=512)
        
        # Get BERT embeddings (without gradient calculation)
        with torch.no_grad():
            outputs = self.model(**inputs)
        
        # Use different layers of BERT for different style aspects
        # [CLS] token embedding captures overall sentence meaning
        sentence_embedding = outputs.last_hidden_state[:, 0, :].numpy()
        
        # Average of all token embeddings captures word-level features
        word_level_features = outputs.last_hidden_state.mean(dim=1).numpy()
        
        # Attention patterns capture structural relationships
        attention = outputs.attentions[-1].mean(dim=1).numpy() if hasattr(outputs, 'attentions') else None
        
        return {
            'sentence_embedding': sentence_embedding,
            'word_level': word_level_features,
            'attention_patterns': attention
        }