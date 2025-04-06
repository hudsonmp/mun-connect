# DelegateProfile Backend Integration Guide

This guide provides instructions for setting up and testing the DelegateProfile backend components in your IDE without requiring any frontend interfaces.

## File Structure

The DelegateProfile system consists of the following core components:

- `delegate_profile.py` - Main class for delegate profile management
- `test_integration.py` - Integration test script for validating the system
- `example_delegate_profile.py` - Example implementation and usage

Supporting modules in subdirectories:
- `delegate-style-analyzer/` - Style analysis tools
- `pdf-transform/` - Document processing pipeline
- `comparison-fingerprint/` - Comparison analysis tools
- `style-assesment/` - Style assessment utilities

## Setup Instructions

### 1. Install Dependencies

First, install the required Python packages:

```bash
pip install supabase
pip install python-dotenv
```

### 2. Configure Environment Variables

You need to set up your Supabase credentials. There are two ways to do this:

#### Option A: Direct Environment Variables

```bash
export NEXT_PUBLIC_SUPABASE_URL='your-supabase-url'
export NEXT_PUBLIC_SUPABASE_ANON_KEY='your-supabase-anon-key'
```

#### Option B: Using a .env File

Create a `.env` file in the `user-context` directory:

```
NEXT_PUBLIC_SUPABASE_URL=your-supabase-url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-supabase-anon-key
```

Then, update the `test_integration.py` script to load the environment variables from this file:

```python
from dotenv import load_dotenv
load_dotenv()  # Add this near the top of the script
```

### 3. Verify Supabase Database

Ensure your Supabase project has a `delegate_analyses` table with the following schema:

| Column Name    | Type           | Description                                |
|----------------| ---------------|--------------------------------------------|
| id             | uuid           | Primary key                                |
| user_id        | uuid           | Foreign key to auth.users                  |
| document_type  | text           | Type of document analyzed                  |
| analysis_type  | text           | Type of analysis performed                 |
| content        | jsonb          | Analysis results as JSON                   |
| created_at     | timestamptz    | Creation timestamp (default: now())        |
| updated_at     | timestamptz    | Last update timestamp (default: now())     |

## Testing Instructions

### Running the Integration Test

The integration test script (`test_integration.py`) provides a comprehensive test of the DelegateProfile system. To run it:

1. Navigate to the `user-context` directory:
   ```bash
   cd /path/to/mun-connect/backend/user-context
   ```

2. Run the test script:
   ```bash
   python test_integration.py
   ```

3. The script will:
   - Verify your environment variables
   - Test the connection to Supabase
   - Create a temporary user profile
   - Store sample analyses
   - Retrieve and display the consolidated profile
   - Clean up test data

### Running the Example Script

The example script (`example_delegate_profile.py`) demonstrates how to use the DelegateProfile in a more realistic scenario:

```bash
python example_delegate_profile.py
```

## Common Issues and Troubleshooting

### Import Errors

If you encounter import errors:

1. Check that you're running the scripts from the correct directory
2. Verify the file structure matches what's expected
3. Try the alternative import method (uncomment the sys.path.append line)

### Supabase Connection Issues

If you can't connect to Supabase:

1. Double-check your environment variables are set correctly
2. Verify your Supabase project is active
3. Confirm you have the correct permissions for the `delegate_analyses` table
4. Check your network connection

### Database Errors

If you encounter database errors:

1. Verify the `delegate_analyses` table exists and has the correct schema
2. Check for Row Level Security (RLS) policies that might be restricting access
3. Confirm your Supabase API key has the necessary permissions

## Custom Testing

To test specific components of the system, you can modify the `test_integration.py` script:

1. To test only the database connection:
   ```python
   if __name__ == "__main__":
       check_environment()
       test_supabase_connection()
   ```

2. To test with a specific user ID:
   ```python
   # Replace the randomly generated UUID with a specific one
   test_user_id = "your-specific-user-id"
   ```

3. To add custom test analyses, create new functions and add them to the test flow.

## Extending the System

To integrate additional analysis modules:

1. Create your analysis function in an appropriate subdirectory
2. Import and call it from your application
3. Use `delegate_profile.store_analysis_result()` to store results 