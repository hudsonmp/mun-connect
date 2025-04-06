class SupabaseInterface:
    def __init__(self, supabase_client):
        self.client = supabase_client
        
    def create_session(self, user_id):
        """Create a new assessment session"""
        data = {
            'user_id': user_id,
            'completed': False,
            'response_count': 0,
            'used_question_ids': [],
            'created_at': 'NOW()'
        }
        response = self.client.table('style_assessment_sessions').insert(data).execute()
        return response.data[0]['id']
        
    def save_response(self, session_id, question_id, chosen_id, beliefs):
        """Save a user response"""
        # Update session
        self.client.table('style_assessment_sessions')\
            .update({
                'response_count': self.client.raw('response_count + 1'),
                'used_question_ids': self.client.raw(f"array_append(used_question_ids, '{question_id}')"),
                'latest_beliefs': beliefs
            })\
            .eq('id', session_id)\
            .execute()
            
        # Save response
        response_data = {
            'session_id': session_id,
            'question_id': question_id,
            'chosen_id': chosen_id,
            'created_at': 'NOW()'
        }
        self.client.table('style_assessment_responses').insert(response_data).execute()