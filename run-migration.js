const { Pool } = require('pg');
const fs = require('fs');
const path = require('path');

// Database connection configuration from .env
const connectionString = 'postgresql://postgres.yfksapziqxrgfrmflnnn:uNKSqj5gKYdqJxCW@aws-0-us-west-1.pooler.supabase.com:5432/postgres';

// Create a new pool
const pool = new Pool({
  connectionString,
});

// Read the SQL file
const sqlFilePath = path.join(__dirname, 'db-migration.sql');
const sql = fs.readFileSync(sqlFilePath, 'utf8');

async function runMigration() {
  const client = await pool.connect();
  
  try {
    console.log('Starting database migration...');
    
    // Begin transaction
    await client.query('BEGIN');
    
    // Execute the SQL script
    await client.query(sql);
    
    // Commit transaction
    await client.query('COMMIT');
    
    console.log('Migration completed successfully!');
  } catch (error) {
    // Rollback transaction on error
    await client.query('ROLLBACK');
    console.error('Migration failed:', error);
  } finally {
    // Release the client back to the pool
    client.release();
    // Close the pool
    await pool.end();
  }
}

// Run the migration
runMigration(); 