#!/bin/bash

# Exit on error
set -e

echo "Deploying main MUN Connect static site..."
# For main project, use current vercel.json
npx vercel deploy --prod

echo "Deploying MUN Connect Dashboard application..."
# For dashboard project, use the dashboard config
echo "Switching to dashboard configuration..."
cp vercel.json vercel.json.bak
cp vercel.dashboard.json vercel.json
npx vercel deploy --prod --name mun-connect-dashboard

# Restore original vercel.json
echo "Restoring main configuration..."
mv vercel.json.bak vercel.json

echo "Deployment completed!"
echo "Main site: https://mun-connect.vercel.app"
echo "Dashboard: https://mun-connect-dashboard.vercel.app"
echo "Make sure to check the Vercel dashboard to confirm both deployments succeeded." 