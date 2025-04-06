from transformers import BertModel, BertTokenizer
import torch
import numpy as np
import os
from datetime import datetime

# Initialize Supabase client
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_KEY")
supabase = SupabaseStyleAssessment(supabase_url, supabase_key)

# BERT extractor
class BERTExtractor:
    def __init__(self):
        self.tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')
        self.model = BertModel.from_pretrained('bert-base-uncased')
        self.model.eval()
    
    def extract_features(self, text):
        # Check if we have cached embedding
        # (Implementation skipped for brevity)
        
        # Tokenize and prepare for BERT
        inputs = self.tokenizer(text, return_tensors="pt", 
                               padding=True, truncation=True, 
                               max_length=512)
        
        # Get BERT embeddings
        with torch.no_grad():
            outputs = self.model(**inputs)
        
        # Use [CLS] token embedding
        embedding = outputs.last_hidden_state[:, 0, :].numpy().flatten()
        
        return embedding

# Example of complete flow
def run_style_assessment(user_id, document_type):
    # Initialize
    bert = BERTExtractor()
    
    # Create session
    session = supabase.create_session(user_id, document_type)
    session_id = session['id']
    
    # Get initial questions
    questions = supabase.get_initial_questions(limit=5)
    
    # Start with first question
    current_question = questions[0]
    response_count = 0
    beliefs = session['latest_beliefs']
    
    # Simulate user interaction
    while response_count < 10:  # Limit to 10 questions for this example
        # Present question to user
        print(f"Question {response_count + 1}:")
        print(f"A: {current_question['sentence_a']}")
        print(f"B: {current_question['sentence_b']}")
        
        # Get user choice (simulated here)
        choice = input("Choose A or B: ").upper()
        chosen_id = current_question['sentence_a_id'] if choice == 'A' else current_question['sentence_b_id']
        
        # Record time (for demonstration)
        response_time = 500  # milliseconds
        
        # Extract BERT features
        features_a = bert.extract_features(current_question['sentence_a'])
        features_b = bert.extract_features(current_question['sentence_b'])
        
        # Cache embeddings
        supabase.store_sentence_embedding(current_question['sentence_a_id'], features_a.tolist())
        supabase.store_sentence_embedding(current_question['sentence_b_id'], features_b.tolist())
        
        # Update Bayesian beliefs (simplified for example)
        # In a real implementation, use the PyMC3 code from earlier
        updated_beliefs = update_beliefs_simplified(beliefs, features_a, features_b, choice)
        
        # Record response
        supabase.record_response(
            session_id,
            current_question['question_external_id'],
            current_question['sentence_a_id'],
            current_question['sentence_b_id'],
            chosen_id,
            updated_beliefs,
            response_time
        )
        
        # Update session state
        response_count += 1
        beliefs = updated_beliefs
        
        # Check if we should end
        if should_end_assessment(beliefs, response_count):
            break
            
        # Get next question
        if response_count < len(questions):
            current_question = questions[response_count]
        else:
            # Get adaptive question based on uncertain dimensions
            uncertain_dims = get_uncertain_dimensions(beliefs)
            used_ids = [q['question_external_id'] for q in questions]
            next_questions = supabase.get_questions_by_dimensions(uncertain_dims, used_ids)
            if next_questions:
                current_question = next_questions[0]
            else:
                # Fallback if no specific questions available
                break
    
    # Complete assessment and generate profile
    supabase.complete_session(session_id, beliefs)
    print("Assessment completed!")
    print(f"Style profile: {beliefs}")

# Helper functions (simplified for example)
def update_beliefs_simplified(current_beliefs, features_a, features_b, choice):
    """Simplified Bayesian update for example purposes."""
    updated = {}
    for dim, values in current_beliefs.items():
        # Simple simulation of Bayesian update
        if choice == 'A':
            new_mean = values['mean'] * 0.8 + 0.2
        else:
            new_mean = values['mean'] * 0.8
        
        # Decrease variance (increase confidence)
        new_var = values['variance'] * 0.9
        
        updated[dim] = {'mean': new_mean, 'variance': new_var}
    
    return updated

def should_end_assessment(beliefs, count):
    """Determine if assessment should end."""
    if count >= 12:
        return True
        
    # Check confidence
    avg_var = np.mean([b['variance'] for b in beliefs.values()])
    return avg_var < 0.05

def get_uncertain_dimensions(beliefs, top_n=2):
    """Get dimensions with highest uncertainty."""
    sorted_dims = sorted(beliefs.items(), key=lambda x: x[1]['variance'], reverse=True)
    return [d[0] for d in sorted_dims[:top_n]]