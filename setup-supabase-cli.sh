#!/bin/bash

# Install Supabase CLI if not already installed
echo "Checking for Supabase CLI..."
if ! command -v supabase &> /dev/null; then
    echo "Installing Supabase CLI..."
    brew install supabase/tap/supabase
fi

# Create a migrations directory if it doesn't exist
mkdir -p migrations

# Copy the SQL file to the migrations directory
cp db-migration.sql migrations/$(date +%Y%m%d%H%M%S)_profile_updates.sql

echo "Supabase CLI setup completed."
echo ""
echo "To execute the SQL commands, please:"
echo "1. Go to https://app.supabase.com"
echo "2. Select your project (URL: https://yfksapziqxrgfrmflnnn.supabase.co)"
echo "3. Navigate to the SQL Editor"
echo "4. Open the db-migration.sql file"
echo "5. Run the SQL commands by clicking the 'Run' button"
echo ""
echo "Alternatively, you can use the Supabase CLI with:"
echo "supabase login"
echo "supabase link --project-ref yfksapziqxrgfrmflnnn"
echo "supabase db push migrations/$(ls -1 migrations | tail -1)" 