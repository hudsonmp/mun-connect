#!/bin/bash

# Exit on error
set -e

echo "Preparing configuration files..."
# Make sure our setup script is executable
chmod +x setup-build.js

echo "Deploying main MUN Connect static site..."
# For main project, use current vercel.json
DEPLOYMENT_TARGET=main npx vercel deploy --prod

echo "Deploying MUN Connect Dashboard application..."
# For dashboard project, use the dashboard config
cp vercel.dashboard.json vercel.json
DEPLOYMENT_TARGET=dashboard npx vercel deploy --prod --name mun-connect-dashboard

# Restore original vercel.json
echo "Cleaning up..."
git checkout -- vercel.json

echo "Deployment completed!"
echo "Main site: https://mun-connect.vercel.app"
echo "Dashboard: https://mun-connect-dashboard.vercel.app"
echo "Make sure to check the Vercel dashboard to confirm both deployments succeeded."
echo "Remember to set up the domains in the Vercel Dashboard if needed." 