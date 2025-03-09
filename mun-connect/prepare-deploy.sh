#!/bin/bash

# Prepare the project for deployment to Vercel

echo "Preparing MUN Connect for deployment..."

# Build the frontend
echo "Building the frontend..."
npm run build

# Create a .vercelignore file to exclude backend files
echo "Creating .vercelignore file..."
cat > .vercelignore << EOL
backend/
docker-compose.yml
Dockerfile
.github/
.env
.env.local
EOL

echo "Project is ready for deployment to Vercel!"
echo "To deploy, run: vercel --prod" 