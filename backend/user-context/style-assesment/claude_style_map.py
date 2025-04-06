class StyleDimensionMapper:
    def __init__(self, style_dimensions=None):
        # Default MUN style dimensions
        self.style_dimensions = style_dimensions or [
            'formality', 'technicality', 'persuasiveness', 
            'structure', 'diplomatic_tone'
        ]
        
        # Pre-trained weights would be loaded here
        # This would normally be trained, but we'll use a simple mapping initially
        self.weights = self._initialize_weights()
        
    def _initialize_weights(self):
        """Initialize weights for mapping BERT features to style dimensions"""
        # In a real implementation, these would be pre-trained on a small dataset
        # For now, we'll use random initialization as a placeholder
        return {dim: np.random.randn(768) for dim in self.style_dimensions}
    
    def map_features(self, bert_features):
        """Map BERT features to style dimensions"""
        sentence_embedding = bert_features['sentence_embedding'].squeeze()
        
        # Calculate style dimension scores using dot product
        style_scores = {}
        for dim, weight in self.weights.items():
            # Dot product + sigmoid to get 0-1 score
            score = 1 / (1 + np.exp(-np.dot(sentence_embedding, weight)))
            style_scores[dim] = float(score)
            
        return style_scores