const { createClient } = require('@supabase/supabase-js');
const fs = require('fs');
const path = require('path');
require('dotenv').config({ path: path.resolve(__dirname, '../.env.local') });

// Get Supabase credentials from environment variables
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseServiceKey = process.env.NEXT_PUBLIC_SUPABASE_SERVICE_ROLE_KEY;

if (!supabaseUrl || !supabaseServiceKey) {
  console.error('ERROR: Missing Supabase credentials in environment variables');
  console.error('Make sure NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_SERVICE_ROLE_KEY are set in .env.local');
  process.exit(1);
}

// Create a Supabase client with the service role key for admin privileges
const supabase = createClient(supabaseUrl, supabaseServiceKey);

async function runMigration() {
  try {
    // Read the migration SQL file
    const migrationFile = path.resolve(__dirname, 'migrations/20240401_chat_persistence.sql');
    const sql = fs.readFileSync(migrationFile, 'utf8');
    
    console.log('Running migration script...');
    
    // Execute the SQL using the Supabase client
    const { error } = await supabase.rpc('pg_execute', { sql_query: sql });
    
    if (error) {
      throw error;
    }
    
    console.log('Migration completed successfully!');
    
    // Verify that the tables were created
    const { data: tables, error: tablesError } = await supabase
      .from('pg_tables')
      .select('*')
      .in('schemaname', ['public']);
      
    if (tablesError) {
      throw tablesError;
    }
    
    console.log('Available tables:');
    tables.forEach(table => {
      if (table.tablename === 'chats' || table.tablename === 'messages') {
        console.log(`✓ ${table.tablename}`);
      } else {
        console.log(`- ${table.tablename}`);
      }
    });
    
  } catch (error) {
    console.error('Migration failed:', error);
    process.exit(1);
  }
}

runMigration(); 