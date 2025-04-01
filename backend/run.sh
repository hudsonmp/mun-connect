#!/bin/bash

# Directory where this script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Check if python3 is installed
if ! command -v python3 &> /dev/null
then
    echo "Python 3 is required but not installed. Please install Python 3 and try again."
    exit 1
fi

# Check if virtual environment exists, if not create one
if [ ! -d "$DIR/venv" ]
then
    echo "Creating virtual environment..."
    python3 -m venv "$DIR/venv"
    
    # Activate virtual environment
    source "$DIR/venv/bin/activate"
    
    # Install required packages
    echo "Installing required packages..."
    pip install -r "$DIR/requirements.txt"
else
    # Activate virtual environment
    source "$DIR/venv/bin/activate"
fi

# Check if .env file exists in the project root
if [ ! -f "$DIR/../.env" ]
then
    echo "Warning: .env file not found in project root."
    echo "Some functionality may not work correctly."
fi

# Make sure Supabase is running
echo "Checking if Supabase is running..."
if ! curl -s http://localhost:54321/health > /dev/null
then
    echo "Warning: Supabase doesn't appear to be running."
    echo "Please start Supabase with 'npx supabase start' for full functionality."
fi

# Run the Flask application
echo "Starting Flask server..."
cd "$DIR"
export FLASK_APP=app.py
export FLASK_ENV=development
python -m flask run --host=0.0.0.0 --port=5001 