import os
from dotenv import load_dotenv
from supabase import create_client, Client
from postgrest.exceptions import APIError

# Load environment variables
load_dotenv()

url = os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")  # Use service role key for admin operations

if not url or not key:
    raise ValueError("Missing Supabase URL or Service Role Key")

# Initialize the Supabase client with service role key for admin operations
supabase: Client = create_client(url, key)

def setup_database():
    """Setup the database schema for MUN Connect."""
    print("Setting up database schema...")
    
    try:
        # Create all tables in a single transaction
        create_table_sql = """
        -- Create profiles table
        CREATE TABLE IF NOT EXISTS public.profiles (
            id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
            email TEXT UNIQUE NOT NULL,
            full_name TEXT,
            avatar_url TEXT,
            school TEXT,
            grade INTEGER,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );

        -- Enable RLS for profiles
        ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

        -- Create RLS policies for profiles
        DROP POLICY IF EXISTS "Users can view their own profile" ON public.profiles;
        CREATE POLICY "Users can view their own profile"
        ON public.profiles FOR SELECT
        USING (auth.uid() = id);

        DROP POLICY IF EXISTS "Users can update their own profile" ON public.profiles;
        CREATE POLICY "Users can update their own profile"
        ON public.profiles FOR UPDATE
        USING (auth.uid() = id);

        -- Create conferences table
        CREATE TABLE IF NOT EXISTS public.conferences (
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

        -- Enable RLS for conferences
        ALTER TABLE public.conferences ENABLE ROW LEVEL SECURITY;

        -- Create RLS policies for conferences
        DROP POLICY IF EXISTS "Users can view their own conferences" ON public.conferences;
        CREATE POLICY "Users can view their own conferences"
        ON public.conferences FOR SELECT
        USING (auth.uid() = user_id);

        DROP POLICY IF EXISTS "Users can insert their own conferences" ON public.conferences;
        CREATE POLICY "Users can insert their own conferences"
        ON public.conferences FOR INSERT
        WITH CHECK (auth.uid() = user_id);

        DROP POLICY IF EXISTS "Users can update their own conferences" ON public.conferences;
        CREATE POLICY "Users can update their own conferences"
        ON public.conferences FOR UPDATE
        USING (auth.uid() = user_id);

        DROP POLICY IF EXISTS "Users can delete their own conferences" ON public.conferences;
        CREATE POLICY "Users can delete their own conferences"
        ON public.conferences FOR DELETE
        USING (auth.uid() = user_id);

        -- Create documents table
        CREATE TABLE IF NOT EXISTS public.documents (
            id SERIAL PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
            title TEXT NOT NULL,
            type TEXT NOT NULL CHECK (type IN ('Position Paper', 'Resolution', 'Speech')),
            committee TEXT NOT NULL,
            conference TEXT NOT NULL,
            content TEXT,
            source_urls TEXT[],
            background_guide_text TEXT,
            formatting_guidelines TEXT,
            additional_questions JSONB,
            progress INTEGER NOT NULL DEFAULT 0 CHECK (progress >= 0 AND progress <= 100),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );

        -- Enable RLS for documents
        ALTER TABLE public.documents ENABLE ROW LEVEL SECURITY;

        -- Create RLS policies for documents
        DROP POLICY IF EXISTS "Users can view their own documents" ON public.documents;
        CREATE POLICY "Users can view their own documents"
        ON public.documents FOR SELECT
        USING (auth.uid() = user_id);

        DROP POLICY IF EXISTS "Users can insert their own documents" ON public.documents;
        CREATE POLICY "Users can insert their own documents"
        ON public.documents FOR INSERT
        WITH CHECK (auth.uid() = user_id);

        DROP POLICY IF EXISTS "Users can update their own documents" ON public.documents;
        CREATE POLICY "Users can update their own documents"
        ON public.documents FOR UPDATE
        USING (auth.uid() = user_id);

        DROP POLICY IF EXISTS "Users can delete their own documents" ON public.documents;
        CREATE POLICY "Users can delete their own documents"
        ON public.documents FOR DELETE
        USING (auth.uid() = user_id);

        -- Create user_stats table
        CREATE TABLE IF NOT EXISTS public.user_stats (
            id SERIAL PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
            conferences_count INTEGER DEFAULT 0,
            documents_count INTEGER DEFAULT 0,
            awards_count INTEGER DEFAULT 0,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            UNIQUE(user_id)
        );

        -- Enable RLS for user_stats
        ALTER TABLE public.user_stats ENABLE ROW LEVEL SECURITY;

        -- Create RLS policies for user_stats
        DROP POLICY IF EXISTS "Users can view their own stats" ON public.user_stats;
        CREATE POLICY "Users can view their own stats"
        ON public.user_stats FOR SELECT
        USING (auth.uid() = user_id);

        DROP POLICY IF EXISTS "Users can update their own stats" ON public.user_stats;
        CREATE POLICY "Users can update their own stats"
        ON public.user_stats FOR UPDATE
        USING (auth.uid() = user_id);

        -- Create MUN onboarding data table for testing
        CREATE TABLE IF NOT EXISTS public.mun_onboarding_data (
            id SERIAL PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
            conference_name TEXT NOT NULL,
            committee_name TEXT NOT NULL,
            position_country TEXT NOT NULL,
            topic TEXT NOT NULL,
            country_stance TEXT,
            key_points TEXT[],
            research_materials JSONB,
            background_info TEXT,
            formatting_preferences JSONB,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            UNIQUE(user_id)
        );

        -- Enable RLS for MUN onboarding data
        ALTER TABLE public.mun_onboarding_data ENABLE ROW LEVEL SECURITY;

        -- Create RLS policies for MUN onboarding data
        DROP POLICY IF EXISTS "Users can view their own MUN onboarding data" ON public.mun_onboarding_data;
        CREATE POLICY "Users can view their own MUN onboarding data"
        ON public.mun_onboarding_data FOR SELECT
        USING (auth.uid() = user_id);

        DROP POLICY IF EXISTS "Users can insert their own MUN onboarding data" ON public.mun_onboarding_data;
        CREATE POLICY "Users can insert their own MUN onboarding data"
        ON public.mun_onboarding_data FOR INSERT
        WITH CHECK (auth.uid() = user_id);

        DROP POLICY IF EXISTS "Users can update their own MUN onboarding data" ON public.mun_onboarding_data;
        CREATE POLICY "Users can update their own MUN onboarding data"
        ON public.mun_onboarding_data FOR UPDATE
        USING (auth.uid() = user_id);

        DROP POLICY IF EXISTS "Users can delete their own MUN onboarding data" ON public.mun_onboarding_data;
        CREATE POLICY "Users can delete their own MUN onboarding data"
        ON public.mun_onboarding_data FOR DELETE
        USING (auth.uid() = user_id);

        -- Create chats table if it doesn't exist
        CREATE TABLE IF NOT EXISTS public.chats (
            id UUID PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
            title TEXT NOT NULL DEFAULT 'New Chat',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );

        -- Enable RLS for chats
        ALTER TABLE public.chats ENABLE ROW LEVEL SECURITY;

        -- Create RLS policies for chats
        DROP POLICY IF EXISTS "Users can view their own chats" ON public.chats;
        CREATE POLICY "Users can view their own chats"
        ON public.chats FOR SELECT
        USING (auth.uid() = user_id);

        DROP POLICY IF EXISTS "Users can insert their own chats" ON public.chats;
        CREATE POLICY "Users can insert their own chats"
        ON public.chats FOR INSERT
        WITH CHECK (auth.uid() = user_id);

        DROP POLICY IF EXISTS "Users can update their own chats" ON public.chats;
        CREATE POLICY "Users can update their own chats"
        ON public.chats FOR UPDATE
        USING (auth.uid() = user_id);

        DROP POLICY IF EXISTS "Users can delete their own chats" ON public.chats;
        CREATE POLICY "Users can delete their own chats"
        ON public.chats FOR DELETE
        USING (auth.uid() = user_id);

        -- Create messages table if it doesn't exist
        CREATE TABLE IF NOT EXISTS public.messages (
            id UUID PRIMARY KEY,
            chat_id UUID NOT NULL REFERENCES public.chats(id) ON DELETE CASCADE,
            role TEXT NOT NULL CHECK (role IN ('user', 'system', 'assistant', 'editor', 'upload', 'error')),
            content TEXT NOT NULL,
            order_index INTEGER NOT NULL,
            metadata JSONB DEFAULT '{}'::jsonb,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );

        -- Enable RLS for messages
        ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;

        -- Create RLS policies for messages
        DROP POLICY IF EXISTS "Users can view messages in their chats" ON public.messages;
        CREATE POLICY "Users can view messages in their chats"
        ON public.messages FOR SELECT
        USING (
            EXISTS (
                SELECT 1 FROM public.chats
                WHERE chats.id = messages.chat_id
                AND chats.user_id = auth.uid()
            )
        );

        DROP POLICY IF EXISTS "Users can insert messages in their chats" ON public.messages;
        CREATE POLICY "Users can insert messages in their chats"
        ON public.messages FOR INSERT
        WITH CHECK (
            EXISTS (
                SELECT 1 FROM public.chats
                WHERE chats.id = messages.chat_id
                AND chats.user_id = auth.uid()
            )
        );

        DROP POLICY IF EXISTS "Users can update messages in their chats" ON public.messages;
        CREATE POLICY "Users can update messages in their chats"
        ON public.messages FOR UPDATE
        USING (
            EXISTS (
                SELECT 1 FROM public.chats
                WHERE chats.id = messages.chat_id
                AND chats.user_id = auth.uid()
            )
        );

        DROP POLICY IF EXISTS "Users can delete messages in their chats" ON public.messages;
        CREATE POLICY "Users can delete messages in their chats"
        ON public.messages FOR DELETE
        USING (
            EXISTS (
                SELECT 1 FROM public.chats
                WHERE chats.id = messages.chat_id
                AND chats.user_id = auth.uid()
            )
        );

        -- Create trigger to create profile and stats on user creation
        CREATE OR REPLACE FUNCTION public.handle_new_user()
        RETURNS TRIGGER AS $$
        BEGIN
            INSERT INTO public.profiles (id, email)
            VALUES (new.id, new.email);

            INSERT INTO public.user_stats (user_id)
            VALUES (new.id);

            RETURN new;
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;

        -- Drop the trigger if it exists
        DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;

        -- Create the trigger
        CREATE TRIGGER on_auth_user_created
            AFTER INSERT ON auth.users
            FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();
        """

        # Execute all SQL commands in a single transaction
        supabase.postgrest.rpc('exec_sql', {'query': create_table_sql}).execute()
        print("Database setup complete!")

    except Exception as e:
        if "Could not find the function" in str(e):
            print("Creating exec_sql function...")
            try:
                # Create the exec_sql function first
                create_function_sql = """
                CREATE OR REPLACE FUNCTION public.exec_sql(query text)
                RETURNS void
                LANGUAGE plpgsql
                SECURITY DEFINER
                AS $$
                BEGIN
                    EXECUTE query;
                END;
                $$;
                """
                
                # Use direct connection to create the function
                import psycopg2
                from urllib.parse import urlparse

                # Parse the Supabase URL to get database connection info
                db_url = os.environ.get("DATABASE_URL")
                if not db_url:
                    raise ValueError("DATABASE_URL environment variable is required")

                conn = psycopg2.connect(db_url)
                conn.autocommit = True
                cur = conn.cursor()
                
                try:
                    cur.execute(create_function_sql)
                    print("Created exec_sql function")
                    
                    # Now try to create the tables again
                    cur.execute(create_table_sql)
                    print("Created tables and policies using direct connection")
                finally:
                    cur.close()
                    conn.close()
                
            except Exception as inner_e:
                print(f"Error creating exec_sql function: {str(inner_e)}")
                raise inner_e
        else:
            print(f"Error setting up database: {str(e)}")
            raise e

if __name__ == "__main__":
    setup_database() 