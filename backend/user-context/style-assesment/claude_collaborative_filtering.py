from sklearn.metrics.pairwise import cosine_similarity

class BERTCollaborativeFilter:
    def __init__(self, db_connection=None):
        self.extractor = BERTStyleFeatureExtractor()
        self.user_profiles = {}  # In-memory store of user profiles
        self.sentence_embeddings = {}  # Cache of sentence embeddings
        self.db = db_connection  # Connection to your database
        
    def add_user_profile(self, user_id, profile):
        """Add or update a user profile"""
        self.user_profiles[user_id] = profile
        
    def get_sentence_embedding(self, sentence_id, sentence_text):
        """Get or compute embedding for a sentence"""
        if sentence_id not in self.sentence_embeddings:
            features = self.extractor.extract_features(sentence_text)
            self.sentence_embeddings[sentence_id] = features['sentence_embedding']
        return self.sentence_embeddings[sentence_id]
        
    def find_similar_users(self, target_profile, top_n=5):
        """Find users with similar style preferences"""
        # Convert profiles to vectors (concatenate dimension means)
        target_vector = np.array([target_profile[dim]['mean'] for dim in sorted(target_profile.keys())])
        
        similarities = []
        for user_id, profile in self.user_profiles.items():
            user_vector = np.array([profile[dim]['mean'] for dim in sorted(profile.keys())])
            sim = cosine_similarity([target_vector], [user_vector])[0][0]
            similarities.append((user_id, sim))
            
        # Return top N similar users
        return sorted(similarities, key=lambda x: x[1], reverse=True)[:top_n]
        
    def get_next_questions(self, user_profile, used_sentence_ids, top_n=3):
        """Get most informative next questions based on similar users"""
        # Find similar users
        similar_users = self.find_similar_users(user_profile)
        
        # Get dimensions with highest uncertainty
        uncertain_dims = sorted(
            user_profile.items(), 
            key=lambda x: x[1]['variance'],
            reverse=True
        )
        top_uncertain_dims = [d[0] for d in uncertain_dims[:2]]
        
        # Get sentence pairs that were informative for similar users
        informative_pairs = self._get_informative_pairs(
            [u[0] for u in similar_users],
            top_uncertain_dims,
            used_sentence_ids
        )
        
        return informative_pairs[:top_n]
        
    def _get_informative_pairs(self, user_ids, dimensions, used_ids):
        """Get sentence pairs that were informative for given users and dimensions"""
        # In a real implementation, this would query your database
        # for sentence pairs that similar users found informative
        
        # Placeholder implementation returning dummy data
        return [
            {
                'sentence_a_id': 'a1', 
                'sentence_b_id': 'b1',
                'sentence_a': 'Placeholder.',
                'sentence_b': 'Placeholder.'
            {
                'sentence_a_id': 'a2', 
                'sentence_b_id': 'b2',
                'sentence_a': 'Placeholder.',
                'sentence_b': 'How many more times must we witness sanctions fail before we acknowledge their ineffectiveness?'
            }
            
        ]