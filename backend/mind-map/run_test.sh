#!/bin/bash

# Run the mind map test script
# This script sets up the environment and runs the test.py script

# Set up colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Setting up environment for mind map test...${NC}"

# Create the indices directory if it doesn't exist
mkdir -p backend/mind-map/indices

# Check if OPENAI_API_KEY is set
if [ -z "$OPENAI_API_KEY" ]; then
    echo -e "${RED}ERROR: OPENAI_API_KEY environment variable is not set!${NC}"
    echo -e "Please set it by running: export OPENAI_API_KEY=your_api_key"
    exit 1
fi

# Activate the virtual environment if it exists
if [ -d ".venv" ]; then
    echo -e "${GREEN}Activating virtual environment...${NC}"
    source .venv/bin/activate
fi

# Install required packages if needed
echo -e "${YELLOW}Checking for required packages...${NC}"
pip install -r backend/mind-map/requirements.txt

# Navigate to the mind-map directory
cd backend/mind-map

echo -e "${GREEN}Running mind map test...${NC}"
python test.py --input sample_background_guide.txt

# Check if the test was successful
if [ $? -eq 0 ]; then
    echo -e "${GREEN}Mind map test completed successfully!${NC}"
    echo -e "Check the output files in the backend/mind-map directory."
    
    # Check if visualization_json.json was created and visualize it
    if [ -f "output_visualization_json.json" ]; then
        echo -e "${YELLOW}Visualizing the mind map...${NC}"
        python visualize.py --input output_visualization_json.json --output mind_map_visualization.png
        
        # Check if visualization was successful
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}Visualization created successfully!${NC}"
            echo -e "Visualization saved as mind_map_visualization.png"
        else
            echo -e "${RED}Visualization failed!${NC}"
        fi
    else
        echo -e "${YELLOW}Skipping visualization: output_visualization_json.json not found.${NC}"
    fi
else
    echo -e "${RED}Mind map test failed!${NC}"
    exit 1
fi

# Return to the original directory
cd ../..

echo -e "${YELLOW}Run complete.${NC}"
exit 0 