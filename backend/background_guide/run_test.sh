#!/bin/bash
# Test script for the background guide processor

set -e  # Exit on error

# Change to the directory containing this script
cd "$(dirname "$0")"

# Check for virtual environment
if [ -d "../../.venv" ]; then
    echo "Activating virtual environment..."
    source ../../.venv/bin/activate
elif [ -d "../venv" ]; then
    echo "Activating virtual environment..."
    source ../venv/bin/activate
else
    echo "No virtual environment found. Creating one..."
    python3 -m venv ../venv
    source ../venv/bin/activate
    
    echo "Installing requirements..."
    pip install -r ../requirements.txt
fi

# Run the test
echo "Running background guide processor test..."
python test.py

# Run the integration test with a sample query
if [ $? -eq 0 ]; then
    echo -e "\nRunning main.py with sample query..."
    python main.py test.py --query "climate security implications" --no-openai --no-aws
fi 