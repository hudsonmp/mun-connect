import os
from dotenv import load_dotenv
from supabase import create_client, Client
import time

# Load environment variables
load_dotenv()

url = os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")  # Note: We need service role key for schema management

if not url or not key:
    raise ValueError("Missing Supabase URL or Service Role Key")

# Initialize the Supabase client with service role key for admin operations
supabase: Client = create_client(url, key)

def setup_database():
    """
    Setup the database schema for MUN Connect.
    This function will create all necessary tables, functions, and policies.
    """
    print("Setting up database schema...")
    
    # Create tables
    create_tables()
    
    # Setup RLS policies
    setup_rls_policies()
    
    # Create functions and triggers
    create_functions_and_triggers()
    
    print("Database schema setup complete!")

def create_tables():
    """Create the necessary tables if they don't exist"""
    print("Creating tables...")
    
    # Conferences table
    create_conferences_table()
    
    # Documents table
    create_documents_table()
    
    # User stats table
    create_user_stats_table()

def create_conferences_table():
    """Create the conferences table"""
    try:
        # Check if table exists
        response = supabase.table("conferences").select("*", count="exact").limit(1).execute()
        print("Conferences table already exists.")
    except Exception:
        print("Creating conferences table...")
        # SQL for creating the conferences table
        sql = """
        CREATE TABLE public.conferences (
            id SERIAL PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            acronym TEXT NOT NULL,
            dates TEXT NOT NULL,
            committee TEXT NOT NULL,
            role TEXT NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('active', 'upcoming', 'completed')),
            progress INTEGER NOT NULL DEFAULT 0 CHECK (progress >= 0 AND progress <= 100),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """
        # Execute raw SQL using the REST API
        supabase.rpc('exec_sql', {'query': sql}).execute()

def create_documents_table():
    """Create the documents table"""
    try:
        # Check if table exists
        response = supabase.table("documents").select("*", count="exact").limit(1).execute()
        print("Documents table already exists.")
    except Exception:
        print("Creating documents table...")
        # SQL for creating the documents table
        sql = """
        CREATE TABLE public.documents (
            id SERIAL PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
            title TEXT NOT NULL,
            type TEXT NOT NULL CHECK (type IN ('Position Paper', 'Resolution', 'Speech')),
            committee TEXT NOT NULL,
            conference TEXT NOT NULL,
            content TEXT,
            progress INTEGER NOT NULL DEFAULT 0 CHECK (progress >= 0 AND progress <= 100),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """
        # Execute raw SQL using the REST API
        supabase.rpc('exec_sql', {'query': sql}).execute()

def create_user_stats_table():
    """Create the user_stats table"""
    try:
        # Check if table exists
        response = supabase.table("user_stats").select("*", count="exact").limit(1).execute()
        print("User stats table already exists.")
    except Exception:
        print("Creating user_stats table...")
        # SQL for creating the user_stats table
        sql = """
        CREATE TABLE public.user_stats (
            id SERIAL PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
            conferences_count INTEGER NOT NULL DEFAULT 0,
            documents_count INTEGER NOT NULL DEFAULT 0,
            awards_count INTEGER NOT NULL DEFAULT 0,
            preferred_topics TEXT[],
            preferred_countries TEXT[],
            is_onboarded BOOLEAN DEFAULT FALSE,
            onboarding_completed_at TIMESTAMP WITH TIME ZONE,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """
        # Execute raw SQL using the REST API
        supabase.rpc('exec_sql', {'query': sql}).execute()

def create_user_writing_profiles_table():
    """Create the user_writing_profiles table to store writing style preferences"""
    try:
        # Check if table exists
        response = supabase.table("user_writing_profiles").select("*", count="exact").limit(1).execute()
        print("User writing profiles table already exists.")
    except Exception:
        print("Creating user_writing_profiles table...")
        # SQL for creating the user_writing_profiles table
        sql = """
        CREATE TABLE public.user_writing_profiles (
            id SERIAL PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
            writing_style TEXT,
            tone TEXT,
            sentence_structure TEXT,
            complexity_level TEXT CHECK (complexity_level IN ('basic', 'intermediate', 'advanced')),
            formality_level TEXT CHECK (formality_level IN ('casual', 'neutral', 'formal', 'very formal')),
            creativity_level TEXT CHECK (creativity_level IN ('factual', 'balanced', 'creative')),
            delegate_style TEXT,
            research_depth TEXT CHECK (research_depth IN ('minimal', 'moderate', 'thorough', 'extensive')),
            argument_structure TEXT,
            sample_document_content TEXT,
            parsed_style_data JSONB,
            consolidated_delegate_profile TEXT,
            delegate_profile_created BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            UNIQUE(user_id)
        );
        """
        # Execute raw SQL using the REST API
        supabase.rpc('exec_sql', {'query': sql}).execute()

def create_document_creation_sessions_table():
    """Create the document_creation_sessions table to store document creation progress"""
    try:
        # Check if table exists
        response = supabase.table("document_creation_sessions").select("*", count="exact").limit(1).execute()
        print("Document creation sessions table already exists.")
    except Exception:
        print("Creating document_creation_sessions table...")
        # SQL for creating the document_creation_sessions table
        sql = """
        CREATE TABLE public.document_creation_sessions (
            id SERIAL PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
            document_type TEXT NOT NULL CHECK (document_type IN ('position_paper', 'resolution', 'speech')),
            committee TEXT,
            country TEXT,
            topic TEXT,
            background_guide_text TEXT,
            extracted_formatting TEXT,
            reference_materials JSONB DEFAULT '[]',
            additional_context TEXT,
            session_data JSONB DEFAULT '{}',
            mind_map JSONB,
            status TEXT NOT NULL CHECK (status IN ('in_progress', 'ready_for_generation', 'generating', 'completed', 'failed')),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """
        # Execute raw SQL using the REST API
        supabase.rpc('exec_sql', {'query': sql}).execute()

def setup_rls_policies():
    """Set up Row Level Security policies"""
    print("Setting up RLS policies...")
    
    # Enable RLS on tables
    enable_rls_on_tables()
    
    # Create policies for conferences table
    create_conferences_policies()
    
    # Create policies for documents table
    create_documents_policies()
    
    # Create policies for user_stats table
    create_user_stats_policies()

def enable_rls_on_tables():
    """Enable Row Level Security on tables"""
    tables = ["conferences", "documents", "user_stats"]
    
    for table in tables:
        sql = f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY;"
        try:
            # Execute raw SQL using the REST API
            supabase.rpc('exec_sql', {'query': sql}).execute()
            print(f"Enabled RLS on {table} table.")
        except Exception as e:
            print(f"Error enabling RLS on {table} table: {str(e)}")

def create_conferences_policies():
    """Create policies for conferences table"""
    policies = [
        {
            "name": "Users can view their own conferences",
            "definition": "CREATE POLICY \"Users can view their own conferences\" ON public.conferences FOR SELECT USING (auth.uid() = user_id);"
        },
        {
            "name": "Users can insert their own conferences",
            "definition": "CREATE POLICY \"Users can insert their own conferences\" ON public.conferences FOR INSERT WITH CHECK (auth.uid() = user_id);"
        },
        {
            "name": "Users can update their own conferences",
            "definition": "CREATE POLICY \"Users can update their own conferences\" ON public.conferences FOR UPDATE USING (auth.uid() = user_id);"
        },
        {
            "name": "Users can delete their own conferences",
            "definition": "CREATE POLICY \"Users can delete their own conferences\" ON public.conferences FOR DELETE USING (auth.uid() = user_id);"
        }
    ]
    
    for policy in policies:
        try:
            # Execute raw SQL using the REST API
            supabase.rpc('exec_sql', {'query': policy["definition"]}).execute()
            print(f"Created policy: {policy['name']}")
        except Exception as e:
            print(f"Error creating policy {policy['name']}: {str(e)}")

def create_documents_policies():
    """Create policies for documents table"""
    policies = [
        {
            "name": "Users can view their own documents",
            "definition": "CREATE POLICY \"Users can view their own documents\" ON public.documents FOR SELECT USING (auth.uid() = user_id);"
        },
        {
            "name": "Users can insert their own documents",
            "definition": "CREATE POLICY \"Users can insert their own documents\" ON public.documents FOR INSERT WITH CHECK (auth.uid() = user_id);"
        },
        {
            "name": "Users can update their own documents",
            "definition": "CREATE POLICY \"Users can update their own documents\" ON public.documents FOR UPDATE USING (auth.uid() = user_id);"
        },
        {
            "name": "Users can delete their own documents",
            "definition": "CREATE POLICY \"Users can delete their own documents\" ON public.documents FOR DELETE USING (auth.uid() = user_id);"
        }
    ]
    
    for policy in policies:
        try:
            # Execute raw SQL using the REST API
            supabase.rpc('exec_sql', {'query': policy["definition"]}).execute()
            print(f"Created policy: {policy['name']}")
        except Exception as e:
            print(f"Error creating policy {policy['name']}: {str(e)}")

def create_user_stats_policies():
    """Create policies for user_stats table"""
    policies = [
        {
            "name": "Users can view their own stats",
            "definition": "CREATE POLICY \"Users can view their own stats\" ON public.user_stats FOR SELECT USING (auth.uid() = user_id);"
        },
        {
            "name": "Users can update their own stats",
            "definition": "CREATE POLICY \"Users can update their own stats\" ON public.user_stats FOR UPDATE USING (auth.uid() = user_id);"
        }
    ]
    
    for policy in policies:
        try:
            # Execute raw SQL using the REST API
            supabase.rpc('exec_sql', {'query': policy["definition"]}).execute()
            print(f"Created policy: {policy['name']}")
        except Exception as e:
            print(f"Error creating policy {policy['name']}: {str(e)}")

def create_user_writing_profiles_policies():
    """Create policies for user_writing_profiles table"""
    policies = [
        {
            "name": "Users can view their own writing profiles",
            "definition": "CREATE POLICY \"Users can view their own writing profiles\" ON public.user_writing_profiles FOR SELECT USING (auth.uid() = user_id);"
        },
        {
            "name": "Users can update their own writing profiles",
            "definition": "CREATE POLICY \"Users can update their own writing profiles\" ON public.user_writing_profiles FOR UPDATE USING (auth.uid() = user_id);"
        },
        {
            "name": "Users can insert their own writing profiles",
            "definition": "CREATE POLICY \"Users can insert their own writing profiles\" ON public.user_writing_profiles FOR INSERT WITH CHECK (auth.uid() = user_id);"
        }
    ]
    
    for policy in policies:
        try:
            # Execute raw SQL using the REST API
            supabase.rpc('exec_sql', {'query': policy["definition"]}).execute()
            print(f"Created policy: {policy['name']}")
        except Exception as e:
            print(f"Error creating policy {policy['name']}: {str(e)}")

def create_document_creation_sessions_policies():
    """Create policies for document_creation_sessions table"""
    policies = [
        {
            "name": "Users can view their own document creation sessions",
            "definition": "CREATE POLICY \"Users can view their own document creation sessions\" ON public.document_creation_sessions FOR SELECT USING (auth.uid() = user_id);"
        },
        {
            "name": "Users can update their own document creation sessions",
            "definition": "CREATE POLICY \"Users can update their own document creation sessions\" ON public.document_creation_sessions FOR UPDATE USING (auth.uid() = user_id);"
        },
        {
            "name": "Users can insert their own document creation sessions",
            "definition": "CREATE POLICY \"Users can insert their own document creation sessions\" ON public.document_creation_sessions FOR INSERT WITH CHECK (auth.uid() = user_id);"
        },
        {
            "name": "Users can delete their own document creation sessions",
            "definition": "CREATE POLICY \"Users can delete their own document creation sessions\" ON public.document_creation_sessions FOR DELETE USING (auth.uid() = user_id);"
        }
    ]
    
    for policy in policies:
        try:
            # Execute raw SQL using the REST API
            supabase.rpc('exec_sql', {'query': policy["definition"]}).execute()
            print(f"Created policy: {policy['name']}")
        except Exception as e:
            print(f"Error creating policy {policy['name']}: {str(e)}")

def create_functions_and_triggers():
    """Create functions and triggers for the database"""
    print("Creating functions and triggers...")
    
    # Create function to handle new user creation
    create_new_user_function()
    
    # Create trigger to run the function when a new user is created
    create_user_trigger()

def create_new_user_function():
    """Create a function to handle new user creation"""
    try:
        sql = """
        CREATE OR REPLACE FUNCTION public.handle_new_user()
        RETURNS TRIGGER AS $$
        BEGIN
          INSERT INTO public.user_stats (user_id)
          VALUES (NEW.id);
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;
        """
        # Execute raw SQL using the REST API
        supabase.rpc('exec_sql', {'query': sql}).execute()
        print("Created handle_new_user function.")
    except Exception as e:
        print(f"Error creating handle_new_user function: {str(e)}")

def create_user_trigger():
    """Create a trigger to run the handle_new_user function when a new user is created"""
    try:
        # Drop the trigger if it exists (to avoid errors when recreating)
        drop_sql = """
        DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
        """
        # Execute raw SQL using the REST API
        supabase.rpc('exec_sql', {'query': drop_sql}).execute()
        
        # Create the trigger
        sql = """
        CREATE TRIGGER on_auth_user_created
          AFTER INSERT ON auth.users
          FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();
        """
        # Execute raw SQL using the REST API
        supabase.rpc('exec_sql', {'query': sql}).execute()
        print("Created on_auth_user_created trigger.")
    except Exception as e:
        print(f"Error creating on_auth_user_created trigger: {str(e)}")

def seed_sample_data():
    """Seed the database with sample data for testing"""
    print("Seeding sample data...")
    
    # Add a test user if not exists
    try:
        user_response = supabase.auth.admin.create_user({
            "email": "test@example.com",
            "password": "password123",
            "email_confirm": True
        })
        user_id = user_response.user.id
        print(f"Created test user with ID: {user_id}")
    except Exception as e:
        print(f"Test user may already exist: {str(e)}")
        # Try to get the user ID if the user already exists
        try:
            users_response = supabase.auth.admin.list_users()
            user_id = next((user.id for user in users_response.users if user.email == "test@example.com"), None)
            if user_id:
                print(f"Found existing test user with ID: {user_id}")
            else:
                print("Could not find existing test user")
                return
        except Exception as get_error:
            print(f"Error retrieving users: {str(get_error)}")
            return
    
    # Add sample conferences
    try:
        conferences = [
            {
                "user_id": user_id,
                "name": "Harvard National Model United Nations",
                "acronym": "HNMUN",
                "dates": "Feb 15-18, 2024",
                "committee": "UN Security Council",
                "role": "France",
                "status": "active",
                "progress": 75
            },
            {
                "user_id": user_id,
                "name": "Yale Model United Nations",
                "acronym": "YMUN",
                "dates": "Jan 19-22, 2024",
                "committee": "World Health Organization",
                "role": "Germany",
                "status": "upcoming",
                "progress": 30
            },
            {
                "user_id": user_id,
                "name": "Princeton Model United Nations Conference",
                "acronym": "PMUNC",
                "dates": "Nov 16-19, 2023",
                "committee": "UN General Assembly",
                "role": "Japan",
                "status": "completed",
                "progress": 100
            }
        ]
        
        for conference in conferences:
            supabase.table("conferences").insert(conference).execute()
        
        print("Added sample conferences.")
    except Exception as e:
        print(f"Error adding sample conferences: {str(e)}")
    
    # Add sample documents
    try:
        documents = [
            {
                "user_id": user_id,
                "title": "Climate Change Position Paper",
                "type": "Position Paper",
                "committee": "UN Security Council",
                "conference": "HNMUN",
                "content": "This is a sample position paper on climate change.",
                "progress": 80
            },
            {
                "user_id": user_id,
                "title": "Resolution on Global Health Crisis",
                "type": "Resolution",
                "committee": "World Health Organization",
                "conference": "YMUN",
                "content": "This is a sample resolution on global health crisis.",
                "progress": 45
            },
            {
                "user_id": user_id,
                "title": "Opening Speech on Nuclear Disarmament",
                "type": "Speech",
                "committee": "UN General Assembly",
                "conference": "PMUNC",
                "content": "This is a sample opening speech on nuclear disarmament.",
                "progress": 100
            }
        ]
        
        for document in documents:
            supabase.table("documents").insert(document).execute()
        
        print("Added sample documents.")
    except Exception as e:
        print(f"Error adding sample documents: {str(e)}")
    
    # Update user stats
    try:
        stats = {
            "conferences_count": 3,
            "documents_count": 3,
            "awards_count": 1
        }
        
        supabase.table("user_stats").update(stats).eq("user_id", user_id).execute()
        
        print("Updated user stats.")
    except Exception as e:
        print(f"Error updating user stats: {str(e)}")

if __name__ == "__main__":
    # First, let's create a stored procedure for executing SQL
    try:
        exec_sql_func = """
        CREATE OR REPLACE FUNCTION exec_sql(query text) RETURNS VOID AS $$
        BEGIN
            EXECUTE query;
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;
        """
        supabase.from_("rpc").select("*").execute()  # Just to check connection
        supabase.rpc('exec_sql', {'query': exec_sql_func}).execute()
        print("Created exec_sql function.")
    except Exception as e:
        print(f"Error creating exec_sql function or it already exists: {str(e)}")
    
    # Setup database schema
    setup_database()
    
    # Wait a moment for the schema changes to propagate
    time.sleep(1)
    
    # Seed sample data
    seed_sample_data() 