const { Pool } = require('pg');
const fs = require('fs');
const path = require('path');

// The connection string is from the .cursor/rules/mcp.json file
const connectionString = 'postgresql://postgres.yfksapziqxrgfrmflnnn:uNKSqj5gKYdqJxCW@aws-0-us-west-1.pooler.supabase.com:5432/postgres';

async function executeSQL() {
  const pool = new Pool({ connectionString });
  
  try {
    // Read the SQL file
    const sqlPath = path.join(__dirname, 'create_profiles_table.sql');
    const sqlContent = fs.readFileSync(sqlPath, 'utf8');
    
    // Execute the SQL commands
    const client = await pool.connect();
    try {
      console.log('Connected to Supabase database');
      console.log('Executing SQL commands...');
      
      await client.query(sqlContent);
      
      console.log('SQL commands executed successfully');
    } finally {
      client.release();
    }
  } catch (error) {
    console.error('Error executing SQL:', error);
  } finally {
    await pool.end();
  }
}

executeSQL(); 