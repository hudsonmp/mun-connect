import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

url = os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
key = os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY")

if not url or not key:
    raise ValueError("Missing Supabase URL or API Key")

# Initialize the Supabase client
supabase: Client = create_client(url, key)

def get_user_by_id(user_id):
    """Get a user by ID."""
    return supabase.auth.admin.get_user_by_id(user_id)

# Conference operations
def get_conferences(user_id):
    """Get all conferences for a user."""
    return supabase.table('conferences').select('*').eq('user_id', user_id).order('created_at', desc=True).execute()

def get_conference(conference_id, user_id):
    """Get a specific conference."""
    return supabase.table('conferences').select('*').eq('id', conference_id).eq('user_id', user_id).single().execute()

def create_conference(user_id, conference_data):
    """Create a new conference."""
    conference_data['user_id'] = user_id
    return supabase.table('conferences').insert(conference_data).execute()

def update_conference(conference_id, user_id, conference_data):
    """Update a conference."""
    return supabase.table('conferences').update(conference_data).eq('id', conference_id).eq('user_id', user_id).execute()

def delete_conference(conference_id, user_id):
    """Delete a conference."""
    return supabase.table('conferences').delete().eq('id', conference_id).eq('user_id', user_id).execute()

# Document operations
def get_documents(user_id):
    """Get all documents for a user."""
    return supabase.table('documents').select('*').eq('user_id', user_id).order('updated_at', desc=True).execute()

def get_document(document_id, user_id):
    """Get a specific document."""
    return supabase.table('documents').select('*').eq('id', document_id).eq('user_id', user_id).single().execute()

def create_document(user_id, document_data):
    """Create a new document."""
    document_data['user_id'] = user_id
    return supabase.table('documents').insert(document_data).execute()

def update_document(document_id, user_id, document_data):
    """Update a document."""
    return supabase.table('documents').update(document_data).eq('id', document_id).eq('user_id', user_id).execute()

def delete_document(document_id, user_id):
    """Delete a document."""
    return supabase.table('documents').delete().eq('id', document_id).eq('user_id', user_id).execute()

# User stats operations
def get_user_stats(user_id):
    """Get user stats."""
    return supabase.table('user_stats').select('*').eq('user_id', user_id).single().execute()

def update_user_stats(user_id, stats_data):
    """Update user stats."""
    return supabase.table('user_stats').update(stats_data).eq('user_id', user_id).execute()

# User writing profile operations
def get_user_writing_profile(user_id):
    """Get the writing profile for a user."""
    return supabase.table('user_writing_profiles').select('*').eq('user_id', user_id).single().execute()

def create_user_writing_profile(user_id, profile_data):
    """Create a writing profile for a user."""
    profile_data['user_id'] = user_id
    return supabase.table('user_writing_profiles').insert(profile_data).execute()

def update_user_writing_profile(user_id, profile_data):
    """Update a user's writing profile."""
    return supabase.table('user_writing_profiles').update(profile_data).eq('user_id', user_id).execute()

def delete_user_writing_profile(user_id):
    """Delete a user's writing profile."""
    return supabase.table('user_writing_profiles').delete().eq('user_id', user_id).execute()

# Document creation session operations
def get_document_creation_sessions(user_id):
    """Get all document creation sessions for a user."""
    return supabase.table('document_creation_sessions').select('*').eq('user_id', user_id).order('created_at', desc=True).execute()

def get_document_creation_session(session_id, user_id):
    """Get a specific document creation session."""
    return supabase.table('document_creation_sessions').select('*').eq('id', session_id).eq('user_id', user_id).single().execute()

def create_document_creation_session(user_id, session_data):
    """Create a new document creation session."""
    session_data['user_id'] = user_id
    session_data['status'] = 'in_progress' if 'status' not in session_data else session_data['status']
    return supabase.table('document_creation_sessions').insert(session_data).execute()

def update_document_creation_session(session_id, user_id, session_data):
    """Update a document creation session."""
    return supabase.table('document_creation_sessions').update(session_data).eq('id', session_id).eq('user_id', user_id).execute()

def delete_document_creation_session(session_id, user_id):
    """Delete a document creation session."""
    return supabase.table('document_creation_sessions').delete().eq('id', session_id).eq('user_id', user_id).execute()

# Check if user has completed onboarding
def check_user_onboarding_status(user_id):
    """Check if a user has completed onboarding."""
    response = supabase.table('user_stats').select('is_onboarded').eq('user_id', user_id).single().execute()
    if response.data and 'is_onboarded' in response.data:
        return response.data['is_onboarded']
    return False

# Mark user as onboarded
def complete_user_onboarding(user_id):
    """Mark a user as having completed onboarding."""
    from datetime import datetime
    return supabase.table('user_stats').update({
        'is_onboarded': True,
        'onboarding_completed_at': datetime.now().isoformat()
    }).eq('user_id', user_id).execute()

# Authentication operations
def sign_up(email, password):
    """Sign up a new user."""
    return supabase.auth.sign_up({"email": email, "password": password})

def sign_in(email, password):
    """Sign in a user."""
    return supabase.auth.sign_in_with_password({"email": email, "password": password})

def sign_out():
    """Sign out the current user."""
    return supabase.auth.sign_out()

def get_session():
    """Get the current session."""
    return supabase.auth.get_session()

def reset_password(email):
    """Send a password reset email."""
    return supabase.auth.reset_password_for_email(email)

# Rate limiting functions
def get_user_rate_limits(user_id):
    """Get rate limiting data for a user."""
    return supabase.table('rate_limits').select('*').eq('user_id', user_id).single().execute()

def update_user_rate_limits(user_id, rate_data):
    """Update rate limiting data for a user."""
    # Check if rate limit record exists
    existing = get_user_rate_limits(user_id)
    
    if existing.data:
        # Update existing record
        return supabase.table('rate_limits').update(rate_data).eq('user_id', user_id).execute()
    else:
        # Create new record
        return supabase.table('rate_limits').insert(rate_data).execute() 