# Manual Deployment Guide for MUN Connect

We've updated the codebase to support separate deployments for the static site and dashboard application. Follow these steps to deploy both:

## 1. Set up the Main Static Site Deployment

1. **Go to Vercel Dashboard**:
   - Open [https://vercel.com/dashboard](https://vercel.com/dashboard)
   - Select your team/account

2. **Navigate to your existing `mun-connect` project**

3. **Go to Settings > Environment Variables**:
   - Add these variables if they don't already exist:
     - `NEXT_PUBLIC_SUPABASE_URL`: Your Supabase URL
     - `NEXT_PUBLIC_SUPABASE_ANON_KEY`: Your Supabase anon key
     - `DEPLOYMENT_TARGET`: Set to `main`

4. **Go to Settings > Git**:
   - Ensure branch is set to `main`

5. **Go to Deployments**:
   - Click "Redeploy" on the latest deployment
   - This will trigger a new build with the updated configuration

## 2. Set up the Dashboard Application Deployment

1. **Go to Vercel Dashboard**:
   - Open [https://vercel.com/dashboard](https://vercel.com/dashboard)
   - Select your team/account

2. **Navigate to your existing `mun-connect-dashboard` project**

3. **Go to Settings > Environment Variables**:
   - Add these variables if they don't already exist:
     - `NEXT_PUBLIC_SUPABASE_URL`: Your Supabase URL
     - `NEXT_PUBLIC_SUPABASE_ANON_KEY`: Your Supabase anon key
     - `DEPLOYMENT_TARGET`: Set to `dashboard`

4. **Go to Settings > Build & Development Settings**:
   - Build Command: `npm run build:dashboard`
   - Development Command: `npm run dev:dashboard`

5. **Go to Settings > Git**:
   - Ensure branch is set to `main`

6. **Go to Deployments**:
   - Click "Redeploy" on the latest deployment
   - This will trigger a new build with the dashboard configuration

## 3. Testing and Verification

After both deployments have completed:

1. Visit your main site (e.g., `mun-connect.vercel.app`)
2. Click on "Login" or "Register"
3. Verify you're redirected to the dashboard site (e.g., `mun-connect-dashboard.vercel.app/login`)
4. Try logging in and verify you remain on the dashboard domain
5. Test that protected routes work correctly

## Troubleshooting

If you encounter build errors:

1. Check Vercel logs for both projects
2. Make sure environment variables are set correctly
3. Ensure the `DEPLOYMENT_TARGET` value is set correctly for each deployment

The key changes in the codebase:

- Added `setup-build.js` to prepare the environment
- Created separate build commands for each deployment target
- Added layout for dashboard area with proper `AuthProvider`
- Updated Next.js configuration to handle different environments 