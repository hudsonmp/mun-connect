#!/bin/bash

# Script to deploy both static and dashboard projects to Vercel

# Set to exit on error
set -e

echo "Deploying MUN Connect projects to Vercel..."

# Deploy static site
echo "Deploying static site..."
cd projects/static-mun-connect
vercel --prod

# Deploy dashboard
echo "Deploying dashboard..."
cd ../dashboard-mun-connect
vercel --prod

echo "Deployment complete!" 