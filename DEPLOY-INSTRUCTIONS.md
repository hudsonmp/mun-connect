# MUN Connect - Deployment Instructions

## Overview

MUN Connect is designed as a dual-application architecture:

1. **Static Marketing Site** - The main site (`munconnect.vercel.app`) which contains static content about the platform
2. **Dashboard Application** - The authenticated application (`dashboard.munconnect.vercel.app`) where users access the platform features

This architecture is similar to how Stripe separates their main website (stripe.com) from their dashboard (dashboard.stripe.com).

## Deployment Setup

### Step 1: Configure Environment Variables

In Vercel, you need to set up the following environment variables:

- `NEXT_PUBLIC_SUPABASE_URL` - Your Supabase project URL
- `NEXT_PUBLIC_SUPABASE_ANON_KEY` - Your Supabase anon/public key

These should be set as team-level environment variables and then linked using the `@` syntax in both project configurations.

### Step 2: Deploy the Main Site

1. Create a new Vercel project for the main marketing site
2. Link it to the repository
3. Set the root directory to `/`
4. Use `vercel.json` as the configuration file
5. Set up a custom domain: `munconnect.vercel.app` (or your preferred domain)

The main site will show the static marketing content with Login/Register buttons that direct users to the dashboard application.

### Step 3: Deploy the Dashboard Application

1. Create a second Vercel project for the dashboard
2. Link it to the same repository
3. Set the root directory to `/`
4. Use `vercel-dashboard.json` as the configuration file
5. Set up a custom domain: `dashboard.munconnect.vercel.app`

The dashboard application will handle all authentication and user-specific features.

### Step 4: Verify Rewrites and Redirects

The configuration in `vercel.json` includes rewrites that will redirect `/dashboard/*` paths on the main site to the dashboard application. 

This ensures that:
- Links to the dashboard from the main site work correctly
- Users who manually type `/dashboard/...` URLs on the main site get directed to the dashboard app

## Local Development

For local development, you'll need to decide which part of the application you want to work on:

### To Work on the Marketing Site:

```bash
npm run dev
```

Access the site at `http://localhost:3000`

### To Work on the Dashboard:

You'll need to modify the `package.json` file to include a separate development script for the dashboard:

```json
"scripts": {
  "dev": "next dev",
  "dev:dashboard": "next dev -p 3001"
}
```

Then run:

```bash
npm run dev:dashboard
```

Access the dashboard at `http://localhost:3001/dashboard`

## Authentication Flow

1. Users visit the marketing site (`munconnect.vercel.app`)
2. They click "Login" or "Register"
3. They are redirected to the dashboard site (`dashboard.munconnect.vercel.app/login` or `/register`)
4. After authentication, they remain on the dashboard site
5. Authentication state is only maintained within the dashboard application

## Troubleshooting

### Authentication Issues

If users experience authentication problems:

1. Check that Supabase environment variables are correctly set in both projects
2. Verify that cookies are being set and maintained correctly
3. Check for CORS issues if making cross-domain API calls

### Deployment Problems

If you encounter deployment issues:

1. Verify that both `vercel.json` and `vercel-dashboard.json` are correctly configured
2. Check that the rewrites in `vercel.json` are pointing to the correct dashboard domain
3. Ensure that environment variables are correctly set in both projects

## Security Considerations

- Auth state is maintained only in the dashboard application
- The marketing site has no access to user data
- Both applications should use HTTPS
- Set appropriate CORS headers if needed
- Consider implementing CSP headers for added security 