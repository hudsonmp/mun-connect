// Script to help connect to Supabase using MCP
require('dotenv').config({ path: '.env.local' });

// Get the connection string from environment variables
const connectionString = process.env.POSTGRES_URL || process.env.SUPABASE_URL;
const supabaseApiUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || process.env.SUPABASE_SERVICE_ROLE_KEY;

if (!connectionString) {
  console.error('Error: POSTGRES_URL/SUPABASE_URL environment variable is not set.');
  console.error('Please make sure your .env.local file contains the POSTGRES_URL or SUPABASE_URL variable.');
  process.exit(1);
}

if (!supabaseApiUrl || !supabaseKey) {
  console.warn('Warning: Supabase API URL or key is missing. Some features may not work properly.');
  console.warn('Make sure NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY are set in your .env.local file.');
}

console.log('=== Supabase MCP Connection Instructions ===');
console.log('\n1. Open Cursor and go to Cursor Settings');
console.log('2. Click on the "Features" tab');
console.log('3. Scroll down to "MCP Servers" section');
console.log('4. Click "+ Add new MCP server"');
console.log('5. Enter the following details:');
console.log('   - Name: Supabase');
console.log('   - Type: command');
console.log('   - Command: npx -y @modelcontextprotocol/server-postgres ' + connectionString);
console.log('\n6. Click "Add" and wait for the server to connect');
console.log('7. You should see a green "Enabled" status when connected successfully');
console.log('\nIf you encounter any issues:');
console.log('- Make sure you have Node.js installed');
console.log('- Try restarting Cursor after adding the MCP server');
console.log('- Check if your Supabase database is accessible from your current network');
console.log('\nYou can also run this command directly in your terminal to test the connection:');
console.log('npx -y @modelcontextprotocol/server-postgres ' + connectionString);
console.log('\nSupabase API URL:', supabaseApiUrl || 'Not set');
console.log('Supabase Key:', supabaseKey ? '[REDACTED]' : 'Not set'); 