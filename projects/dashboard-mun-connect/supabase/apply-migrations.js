const { createClient } = require('@supabase/supabase-js');
const fs = require('fs');
const path = require('path');

// Load environment variables
require('dotenv').config();

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

if (!supabaseUrl || !supabaseServiceKey) {
  console.error('Missing Supabase credentials. Please check your .env file.');
  process.exit(1);
}

// Create Supabase client with service role key for admin privileges
const supabase = createClient(supabaseUrl, supabaseServiceKey);

async function applyMigrations() {
  try {
    const migrationsDir = path.join(__dirname, 'migrations');
    const files = fs.readdirSync(migrationsDir)
      .filter(file => file.endsWith('.sql'))
      .sort(); // Sort to ensure migrations run in order

    console.log(`Found ${files.length} migration files to apply.`);

    for (const file of files) {
      console.log(`Applying migration: ${file}`);
      const filePath = path.join(migrationsDir, file);
      const sql = fs.readFileSync(filePath, 'utf8');

      // Execute the SQL
      const { error } = await supabase.rpc('exec_sql', { sql });

      if (error) {
        console.error(`Error applying migration ${file}:`, error);
        process.exit(1);
      }

      console.log(`Successfully applied migration: ${file}`);
    }

    console.log('All migrations applied successfully!');
  } catch (error) {
    console.error('Error applying migrations:', error);
    process.exit(1);
  }
}

applyMigrations(); 