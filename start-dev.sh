#!/bin/bash

# Start the Docker containers
echo "Starting MUN Connect development environment..."
docker-compose up -d

# Wait for the containers to start
echo "Waiting for containers to start..."
sleep 5

# Create database tables
echo "Creating database tables..."
docker-compose exec flask_api python migrations/create_tables.py

echo "MUN Connect development environment is ready!"
echo "Frontend: http://localhost:3000"
echo "Backend API: http://localhost:5000"
echo "pgAdmin: http://localhost:5050"
echo ""
echo "To stop the environment, run: docker-compose down" 