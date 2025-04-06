#!/bin/bash

echo "Starting MUN Connect Testing Platform"
echo "------------------------------------"

# Kill any running Next.js instances first
echo "Killing any running servers..."
./kill-servers.sh

# Start the testing platform
echo "Starting the testing platform..."
npm run test-platform

# Note: This will run in the foreground. To stop, press Ctrl+C 