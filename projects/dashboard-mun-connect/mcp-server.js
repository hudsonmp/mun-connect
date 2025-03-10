// Simple MCP server for local development

const express = require('express');
const cors = require('cors');
const { Pool } = require('pg');
const app = express();
const port = 8080;

// Enable CORS for all routes
app.use(cors({
  origin: '*',
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization']
}));

// Configure PostgreSQL connection
const pool = new Pool({
  user: process.env.POSTGRES_USER || 'postgres',
  host: process.env.POSTGRES_HOST || 'supabase_db',
  database: process.env.POSTGRES_DATABASE || 'postgres',
  password: process.env.POSTGRES_PASSWORD || 'postgres',
  port: 5432,
});

// Middleware to parse JSON bodies
app.use(express.json());

// Health check endpoint
app.get('/', (req, res) => {
  res.json({ status: 'MCP Server is running' });
});

// Profiles API
app.get('/profiles', async (req, res) => {
  try {
    const result = await pool.query('SELECT * FROM profiles');
    res.json(result.rows);
  } catch (error) {
    console.error('Error fetching profiles:', error);
    res.status(500).json({ error: error.message });
  }
});

app.get('/profiles/:id', async (req, res) => {
  try {
    const { id } = req.params;
    const result = await pool.query('SELECT * FROM profiles WHERE id = $1', [id]);
    
    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Profile not found' });
    }
    
    res.json(result.rows[0]);
  } catch (error) {
    console.error('Error fetching profile:', error);
    res.status(500).json({ error: error.message });
  }
});

app.post('/profiles', async (req, res) => {
  try {
    const profile = req.body;
    const fields = Object.keys(profile).join(', ');
    const placeholders = Object.keys(profile).map((_, i) => `$${i + 1}`).join(', ');
    const values = Object.values(profile);
    
    const query = `INSERT INTO profiles (${fields}) VALUES (${placeholders}) RETURNING *`;
    const result = await pool.query(query, values);
    
    res.status(201).json(result.rows[0]);
  } catch (error) {
    console.error('Error creating profile:', error);
    res.status(500).json({ error: error.message });
  }
});

app.put('/profiles/:id', async (req, res) => {
  try {
    const { id } = req.params;
    const profile = req.body;
    
    // Handle the upsert operation manually
    const checkResult = await pool.query('SELECT * FROM profiles WHERE id = $1', [id]);
    
    if (checkResult.rows.length === 0) {
      // Insert new profile if it doesn't exist
      if (!profile.id) {
        profile.id = id;
      }
      
      const fields = Object.keys(profile).join(', ');
      const placeholders = Object.keys(profile).map((_, i) => `$${i + 1}`).join(', ');
      const values = Object.values(profile);
      
      const query = `INSERT INTO profiles (${fields}) VALUES (${placeholders}) RETURNING *`;
      const result = await pool.query(query, values);
      
      return res.status(201).json(result.rows[0]);
    } else {
      // Update existing profile
      const setClause = Object.keys(profile)
        .filter(key => key !== 'id')
        .map((key, i) => `${key} = $${i + 2}`)
        .join(', ');
      const values = [id, ...Object.values(profile).filter((_, i) => Object.keys(profile)[i] !== 'id')];
      
      const query = `UPDATE profiles SET ${setClause} WHERE id = $1 RETURNING *`;
      const result = await pool.query(query, values);
      
      return res.json(result.rows[0]);
    }
  } catch (error) {
    console.error('Error updating profile:', error);
    res.status(500).json({ error: error.message });
  }
});

// Add Supabase-style REST API for table operations
app.get('/rest/v1/:table', async (req, res) => {
  try {
    const table = req.params.table;
    // Handle query parameters for filtering
    const filters = req.query;
    let query = `SELECT * FROM ${table}`;
    
    if (Object.keys(filters).length > 0) {
      const filterKeys = Object.keys(filters).filter(key => key !== 'select');
      if (filterKeys.length > 0) {
        query += ' WHERE ';
        query += filterKeys.map(key => `${key} = '${filters[key]}'`).join(' AND ');
      }
    }
    
    const result = await pool.query(query);
    res.json(result.rows);
  } catch (error) {
    console.error(`Error fetching from ${req.params.table}:`, error);
    res.status(500).json({ error: error.message });
  }
});

app.get('/rest/v1/:table/:id', async (req, res) => {
  try {
    const { table, id } = req.params;
    const result = await pool.query(`SELECT * FROM ${table} WHERE id = $1`, [id]);
    
    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Not found' });
    }
    
    res.json(result.rows[0]);
  } catch (error) {
    console.error(`Error fetching from ${req.params.table}:`, error);
    res.status(500).json({ error: error.message });
  }
});

app.post('/rest/v1/:table', async (req, res) => {
  try {
    const { table } = req.params;
    const data = req.body;
    
    const fields = Object.keys(data).join(', ');
    const placeholders = Object.keys(data).map((_, i) => `$${i + 1}`).join(', ');
    const values = Object.values(data);
    
    const query = `INSERT INTO ${table} (${fields}) VALUES (${placeholders}) RETURNING *`;
    const result = await pool.query(query, values);
    
    res.status(201).json(result.rows[0]);
  } catch (error) {
    console.error(`Error inserting into ${req.params.table}:`, error);
    res.status(500).json({ error: error.message });
  }
});

app.post('/rest/v1/:table/upsert', async (req, res) => {
  try {
    const { table } = req.params;
    const data = req.body;
    
    if (!data.id) {
      return res.status(400).json({ error: 'ID is required for upsert' });
    }
    
    // Check if record exists
    const checkResult = await pool.query(`SELECT id FROM ${table} WHERE id = $1`, [data.id]);
    
    if (checkResult.rows.length === 0) {
      // Insert
      const fields = Object.keys(data).join(', ');
      const placeholders = Object.keys(data).map((_, i) => `$${i + 1}`).join(', ');
      const values = Object.values(data);
      
      const query = `INSERT INTO ${table} (${fields}) VALUES (${placeholders}) RETURNING *`;
      const result = await pool.query(query, values);
      
      return res.status(201).json(result.rows[0]);
    } else {
      // Update
      const setClause = Object.keys(data)
        .filter(key => key !== 'id')
        .map((key, i) => `${key} = $${i + 2}`)
        .join(', ');
      const values = [data.id, ...Object.values(data).filter((_, i) => Object.keys(data)[i] !== 'id')];
      
      const query = `UPDATE ${table} SET ${setClause} WHERE id = $1 RETURNING *`;
      const result = await pool.query(query, values);
      
      return res.json(result.rows[0]);
    }
  } catch (error) {
    console.error(`Error upserting into ${req.params.table}:`, error);
    res.status(500).json({ error: error.message });
  }
});

// Mock Supabase auth endpoints
app.post('/auth/v1/token', (req, res) => {
  res.json({
    access_token: 'mock_access_token',
    refresh_token: 'mock_refresh_token',
    user: {
      id: '00000000-0000-0000-0000-000000000000',
      email: 'test@example.com',
    }
  });
});

app.get('/auth/v1/user', (req, res) => {
  res.json({
    id: '00000000-0000-0000-0000-000000000000',
    email: 'test@example.com',
    role: 'authenticated'
  });
});

// Mock storage endpoints
app.post('/storage/v1/object/:bucket', (req, res) => {
  res.status(200).json({
    Key: `${req.params.bucket}/${Date.now()}.png`,
    Bucket: req.params.bucket,
    ETag: 'mock-etag'
  });
});

// Start the server
app.listen(port, () => {
  console.log(`MCP Server running at http://localhost:${port}`);
  console.log('Environment:', {
    POSTGRES_USER: process.env.POSTGRES_USER || 'postgres',
    POSTGRES_HOST: process.env.POSTGRES_HOST || 'supabase_db',
    POSTGRES_DATABASE: process.env.POSTGRES_DATABASE || 'postgres',
  });
}); 