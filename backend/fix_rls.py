import os
from dotenv import load_dotenv
import psycopg2

# Load environment variables
load_dotenv()

def fix_rls_policies():
    """Update RLS policies for conferences table and check users."""
    
    # SQL to update RLS policies
    sql = '''
    -- Drop and recreate RLS policies for conferences
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
    '''
    
    try:
        # Connect to the database
        db_url = os.environ.get('DATABASE_URL')
        if not db_url:
            raise ValueError('DATABASE_URL environment variable not found')
        
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        cur = conn.cursor()
        
        # Update RLS policies
        cur.execute(sql)
        print('RLS policies updated successfully')
        
        # Check for existing users
        cur.execute('SELECT id, email FROM auth.users')
        users = cur.fetchall()
        print(f'Found {len(users)} users:')
        for user in users:
            print(f'ID: {user[0]}, Email: {user[1]}')
        
        # If no users exist, create a test user
        if len(users) == 0:
            print('Creating a test user...')
            test_user_sql = '''
            INSERT INTO auth.users 
            (id, email, encrypted_password, email_confirmed_at) 
            VALUES 
            ('00000000-0000-0000-0000-000000000000', 'test@example.com', 
            '$2a$10$nKOJiK6b.Jnv0Jw7PyuaX.D0BCGG0VrvBYPuXbctW9lkI8QRZcwKO', now()) 
            ON CONFLICT DO NOTHING;
            '''
            cur.execute(test_user_sql)
            print('Test user created with email: test@example.com and password: password123')
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f'Error: {e}')

if __name__ == "__main__":
    fix_rls_policies() 