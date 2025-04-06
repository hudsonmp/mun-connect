class BERTStyleAssessmentSystem:
    def __init__(self, supabase_client=None):
        self.extractor = BERTStyleFeatureExtractor()
        self.mapper = StyleDimensionMapper()
        self.dimensions = ['formality', 'technicality', 'persuasiveness', 'structure', 'diplomatic_tone']
        
        # Bayesian and collaborative components
        self.bayesian = BayesianStyleProfiler(self.dimensions)
        self.collaborative = BERTCollaborativeFilter()
        
        # Database client
        self.db = supabase_client
        
        # Initial questions (would be loaded from database)
        self.initial_questions = self._load_initial_questions()
        
    def _load_initial_questions(self):
        """Load initial fixed set of questions"""
        # These would be carefully designed to cover different style dimensions
        return [
            {
                'id': 1,
                'sentence_a_id': 'i1a', 
                'sentence_b_id': 'i1b',
                'sentence_a': 'The delegation of France firmly believes that immediate action is required to address the humanitarian crisis.',
                'sentence_b': 'France calls for swift intervention in this humanitarian crisis which demands our urgent attention.'
            },
            {
                'id': 2,
                'sentence_a_id': 'i2a', 
                'sentence_b_id': 'i2b',
                'sentence_a': 'Statistical evidence demonstrates that sanctions have failed to curb nuclear proliferation in 82% of historical cases.',
                'sentence_b': 'How many more times must we witness sanctions fail before we acknowledge they cannot stop nuclear proliferation?'
            },
            # Add 3 more initial questions
        ]
        
    def start_assessment(self, user_id):
        """Begin the assessment process"""
        # Create session in database
        session_id = self._create_session(user_id)
        
        # Return first question
        return {
            'session_id': session_id,
            'question': self.initial_questions[0],
            'progress': {
                'current': 1,
                'total': 10,  # Estimated total questions
                'percent': 10
            }
        }
        
    def record_response(self, session_id, question_id, chosen_id):
        """Record user response and update models"""
        # Get question details
        question = self._get_question(question_id)
        
        # Extract BERT features for both sentences
        features_a = self.extractor.extract_features(question['sentence_a'])
        features_b = self.extractor.extract_features(question['sentence_b'])
        
        # Update Bayesian beliefs
        chosen = 'A' if chosen_id == question['sentence_a_id'] else 'B'
        updated_beliefs = self.bayesian.update_beliefs(features_a, features_b, chosen)
        
        # Record in database
        self._save_response(session_id, question_id, chosen_id, updated_beliefs)
        
        # Get session details
        session = self._get_session(session_id)
        response_count = session['response_count']
        
        # Determine next question
        if response_count < len(self.initial_questions):
            # Still in initial fixed set
            next_question = self.initial_questions[response_count]
        else:
            # Use collaborative filtering to get next question
            used_ids = session['used_question_ids']
            next_questions = self.collaborative.get_next_questions(
                updated_beliefs, 
                used_ids
            )
            next_question = next_questions[0]  # Take first recommendation
            
        # Check if we should end assessment
        if self._should_end_assessment(session, updated_beliefs):
            return self._complete_assessment(session_id)
            
        # Return next question
        return {
            'session_id': session_id,
            'question': next_question,
            'progress': {
                'current': response_count + 1,
                'total': self._estimate_total_questions(updated_beliefs),
                'percent': int((response_count + 1) / self._estimate_total_questions(updated_beliefs) * 100)
            }
        }
        
    def _should_end_assessment(self, session, beliefs):
        """Determine if we have enough information to end assessment"""
        # Check if we've reached minimum questions
        if session['response_count'] < 8:
            return False
            
        # Check if we've reached maximum questions
        if session['response_count'] >= 12:
            return True
            
        # Check if we have high confidence across dimensions
        avg_variance = np.mean([beliefs[d]['variance'] for d in self.dimensions])
        return avg_variance < 0.05  # Threshold for sufficient confidence
        
    def _estimate_total_questions(self, beliefs):
        """Estimate total questions needed based on current uncertainty"""
        avg_variance = np.mean([beliefs[d]['variance'] for d in self.dimensions])
        
        # More uncertainty = more questions needed
        if avg_variance > 0.15:
            return 12
        elif avg_variance > 0.10:
            return 10
        else:
            return 8
            
    def _complete_assessment(self, session_id):
        """Complete the assessment and generate final profile"""
        session = self._get_session(session_id)
        latest_beliefs = session['latest_beliefs']
        
        # Generate user-friendly profile
        profile = self._generate_user_profile(latest_beliefs)
        
        # Update session in database
        self._update_session(session_id, {'completed': True})
        
        return {
            'session_id': session_id,
            'completed': True,
            'profile': profile
        }
        
    def _generate_user_profile(self, beliefs):
        """Generate user-friendly profile from beliefs"""
        # Map numerical values to descriptive labels
        labels = {
            'formality': {
                'low': 'Conversational and accessible',
                'medium': 'Balanced formality',
                'high': 'Highly formal and academic'
            },
            'technicality': {
                'low': 'Clear and straightforward',
                'medium': 'Moderately technical',
                'high': 'Highly technical and precise'
            },
            'persuasiveness': {
                'low': 'Factual and objective',
                'medium': 'Moderately persuasive',
                'high': 'Strongly persuasive and emotional'
            },
            'structure': {
                'low': 'Flowing and narrative',
                'medium': 'Moderately structured',
                'high': 'Highly structured and organized'
            },
            'diplomatic_tone': {
                'low': 'Direct and assertive',
                'medium': 'Diplomatically balanced',
                'high': 'Highly diplomatic and nuanced'
            }
        }
        
        # Convert numerical scores to labels
        profile = {}
        for dim, belief in beliefs.items():
            score = belief['mean']
            if score < 0.33:
                label = 'low'
            elif score < 0.66:
                label = 'medium'
            else:
                label = 'high'
            
            profile[dim] = {
                'score': score,
                'confidence': 1 - belief['variance'],
                'label': labels[dim][label]
            }
            
        return profile