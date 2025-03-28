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
        # Create the conferences table
        print("Creating conferences table...")
        create_table_sql = """
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

        -- Enable RLS
        ALTER TABLE public.conferences ENABLE ROW LEVEL SECURITY;

        -- Create RLS policies
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
                    
                    # Now try to create the table again
                    cur.execute(create_table_sql)
                    print("Created table and policies using direct connection")
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