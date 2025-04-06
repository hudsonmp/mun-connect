from supabase import create_client
import os
import json
import numpy as np
import time
from datetime import datetime

class SupabaseStyleAssessment:
    def __init__(self, supabase_url, supabase_key):
        """Initialize Supabase client for style assessment."""
        self.supabase = create_client(supabase_url, supabase_key)
        
    def get_initial_questions(self, limit=5):
        """Retrieve initial assessment questions."""
        response = self.supabase.table('question_pool')\
            .select('*')\
            .eq('is_initial', True)\
            .order('question_order', ascending=True)\
            .limit(limit)\
            .execute()
            
        return response.data
    
    def get_questions_by_dimensions(self, dimensions, exclude_ids=None, limit=3):
        """Get questions targeting specific style dimensions."""
        query = self.supabase.table('question_pool')\
            .select('*')
            
        # Filter by dimensions
        for dim in dimensions:
            query = query.contains('dimension_tags', [dim])
            
        # Exclude already used questions
        if exclude_ids and len(exclude_ids) > 0:
            query = query.not_in('question_external_id', exclude_ids)
            
        response = query.limit(limit).execute()
        return response.data
    
    def create_session(self, user_id, document_type):
        """Create a new style assessment session."""
        data = {
            'user_id': user_id,
            'document_type': document_type,
            'completed': False,
            'response_count': 0,
            'used_question_ids': [],
            'latest_beliefs': {
                'formality': {'mean': 0.5, 'variance': 0.25},
                'technicality': {'mean': 0.5, 'variance': 0.25},
                'persuasiveness': {'mean': 0.5, 'variance': 0.25},
                'structure': {'mean': 0.5, 'variance': 0.25},
                'diplomatic_tone': {'mean': 0.5, 'variance': 0.25}
            }
        }
        
        response = self.supabase.table('style_assessment_sessions')\
            .insert(data)\
            .execute()
            
        return response.data[0]
    
    def get_session(self, session_id):
        """Get session details."""
        response = self.supabase.table('style_assessment_sessions')\
            .select('*')\
            .eq('id', session_id)\
            .single()\
            .execute()
            
        return response.data
    
    def record_response(self, session_id, question_id, sentence_a_id, 
                        sentence_b_id, chosen_id, beliefs_after, response_time_ms=None):
        """Record user's response to a question."""
        # Get session first
        session = self.get_session(session_id)
        
        # Update session data
        used_ids = session['used_question_ids'] or []
        used_ids.append(question_id)
        
        session_update = {
            'response_count': session['response_count'] + 1,
            'used_question_ids': used_ids,
            'latest_beliefs': beliefs_after
        }
        
        self.supabase.table('style_assessment_sessions')\
            .update(session_update)\
            .eq('id', session_id)\
            .execute()
        
        # Record response
        response_data = {
            'session_id': session_id,
            'question_id': question_id,
            'sentence_a_id': sentence_a_id,
            'sentence_b_id': sentence_b_id,
            'chosen_id': chosen_id,
            'response_time_ms': response_time_ms,
            'beliefs_after': beliefs_after
        }
        
        self.supabase.table('style_assessment_responses')\
            .insert(response_data)\
            .execute()
            
        return True
    
    def complete_session(self, session_id, final_profile):
        """Mark session as complete and store final profile."""
        # Get session
        session = self.get_session(session_id)
        
        # Update session
        self.supabase.table('style_assessment_sessions')\
            .update({
                'completed': True,
                'completed_at': datetime.now().isoformat()
            })\
            .eq('id', session_id)\
            .execute()
        
        # Store or update user profile
        dimension_values = {dim: values['mean'] for dim, values in final_profile.items()}
        confidence_scores = {dim: 1 - values['variance'] for dim, values in final_profile.items()}
        
        # Generate style labels based on scores
        style_labels = self._generate_style_labels(dimension_values)
        
        # Determine main style cluster (simplified)
        main_style = max(dimension_values.items(), key=lambda x: x[1])[0]
        
        profile_data = {
            'user_id': session['user_id'],
            'document_type': session['document_type'],
            'dimension_values': dimension_values,
            'confidence_scores': confidence_scores,
            'main_style_cluster': main_style,
            'style_labels': style_labels,
            'updated_at': datetime.now().isoformat()
        }
        
        # Check if profile exists
        existing = self.supabase.table('user_style_profiles')\
            .select('id')\
            .eq('user_id', session['user_id'])\
            .eq('document_type', session['document_type'])\
            .execute()
            
        if existing.data:
            # Update existing profile
            self.supabase.table('user_style_profiles')\
                .update(profile_data)\
                .eq('user_id', session['user_id'])\
                .eq('document_type', session['document_type'])\
                .execute()
        else:
            # Create new profile
            self.supabase.table('user_style_profiles')\
                .insert(profile_data)\
                .execute()
                
        return True
    
    def store_sentence_embedding(self, sentence_id, embedding_vector):
        """Store sentence embedding in cache."""
        data = {
            'sentence_id': sentence_id,
            'embedding': embedding_vector
        }
        
        # Upsert (insert or update)
        self.supabase.table('sentence_embeddings')\
            .upsert(data, on_conflict='sentence_id')\
            .execute()
            
        return True
    
    def get_sentence_embedding(self, sentence_id):
        """Retrieve cached sentence embedding."""
        response = self.supabase.table('sentence_embeddings')\
            .select('embedding')\
            .eq('sentence_id', sentence_id)\
            .single()\
            .execute()
            
        if response.data:
            return response.data['embedding']
        return None
    
    def find_similar_users(self, dimension_values, document_type, limit=5):
        """Find users with similar style profiles."""
        # Get all profiles for this document type
        response = self.supabase.table('user_style_profiles')\
            .select('user_id, dimension_values')\
            .eq('document_type', document_type)\
            .execute()
            
        profiles = response.data
        if not profiles:
            return []
            
        # Calculate similarities
        similarities = []
        for profile in profiles:
            other_values = profile['dimension_values']
            
            # Calculate cosine similarity
            sim_score = self._calculate_similarity(dimension_values, other_values)
            similarities.append((profile['user_id'], sim_score))
            
        # Return top N most similar
        return sorted(similarities, key=lambda x: x[1], reverse=True)[:limit]
    
    def _calculate_similarity(self, values1, values2):
        """Calculate cosine similarity between two style profiles."""
        # Ensure same dimensions in same order
        dims = sorted(set(values1.keys()) & set(values2.keys()))
        
        if not dims:
            return 0.0
            
        # Create vectors
        vec1 = np.array([values1[d] for d in dims])
        vec2 = np.array([values2[d] for d in dims])
        
        # Calculate cosine similarity
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
            
        return dot_product / (norm1 * norm2)
    
    def _generate_style_labels(self, dimension_values):
        """Generate human-readable style labels based on dimension scores."""
        labels = {}
        
        # Define thresholds and labels
        thresholds = {'low': 0.33, 'medium': 0.66, 'high': 1.0}
        
        # Style descriptions
        descriptions = {
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
        
        # Generate labels for each dimension
        for dim, score in dimension_values.items():
            if dim in descriptions:
                # Determine label based on thresholds
                label = 'low'
                for level, threshold in thresholds.items():
                    if score <= threshold:
                        label = level
                        break
                
                # Add description for this dimension
                labels[dim] = descriptions[dim][label]
        
        return labels