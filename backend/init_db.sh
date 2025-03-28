#!/bin/bash

# Directory where this script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Check if python3 is installed
if ! command -v python3 &> /dev/null
then
    echo "Python 3 is required but not installed. Please install Python 3 and try again."
    exit 1
fi

# Check if pip is installed
if ! command -v pip3 &> /dev/null
then
    echo "pip3 is required but not installed. Please install pip3 and try again."
    exit 1
fi

# Check if virtual environment exists, if not create one
if [ ! -d "$DIR/venv" ]
then
    echo "Creating virtual environment..."
    python3 -m venv "$DIR/venv"
fi

# Activate virtual environment
source "$DIR/venv/bin/activate"

# Install required packages
echo "Installing required packages..."
pip install -r "$DIR/requirements.txt"

# Check if .env file exists in the project root
if [ ! -f "$DIR/../.env" ]
then
    echo "Error: .env file not found in project root."
    echo "Please create a .env file with the following variables:"
    echo "NEXT_PUBLIC_SUPABASE_URL=your_supabase_url"
    echo "NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key"
    echo "SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key"
    exit 1
fi

# Make sure Supabase is running
echo "Checking if Supabase is running..."
if ! curl -s http://localhost:54321/health > /dev/null
then
    echo "Error: Supabase is not running."
    echo "Please start Supabase with 'npx supabase start' before initializing the database."
    exit 1
fi

# Run the schema.py script to initialize the database
echo "Initializing database schema..."
python "$DIR/schema.py"

echo "Database initialization completed." 