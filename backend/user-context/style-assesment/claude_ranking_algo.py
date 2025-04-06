class StyleAssessmentSystem:
    def __init__(self, sentence_database, kmeans_model):
        self.sentence_database = sentence_database
        self.kmeans_model = kmeans_model
        self.cluster_specific_questions = load_cluster_questions()
        self.dimension_indices = load_dimension_indices()
        
    def get_initial_questions(self):
        """Return fixed set of initial questions."""
        return INITIAL_QUESTION_SET  # 5 pre-defined question pairs
        
    def determine_cluster(self, initial_responses):
        """Determine style cluster based on initial responses."""
        features = np.array(initial_responses).reshape(1, -1)
        return self.kmeans_model.predict(features)[0]
        
    def get_followup_questions(self, cluster, previous_responses):
        """Get cluster-specific follow-up questions."""
        # Get question set for this cluster
        question_set = self.cluster_specific_questions[cluster]
        
        # Return 5-7 most informative questions from this set
        # based on previous responses
        return self._select_informative_questions(question_set, previous_responses)
        
    def calculate_style_profile(self, all_responses):
        """Calculate final style profile from all responses."""
        dimensions = {}
        for dim_name, indices in self.dimension_indices.items():
            # Calculate each dimension score
            dim_responses = [all_responses[i] for i in indices if i < len(all_responses)]
            dimensions[dim_name] = np.mean(dim_responses)
            
        return {
            'dimensions': dimensions,
            'cluster': self.determine_cluster(all_responses)
        }