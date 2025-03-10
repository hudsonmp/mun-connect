# MUN Connect - Project Structure

This repository contains two separate Next.js applications that are deployed independently on Vercel:

1. **Static Site** (`static-mun-connect/`): Contains the landing page and public content
2. **Dashboard Application** (`dashboard-mun-connect/`): Contains the authenticated dashboard and all app functionality

## Deployment Architecture

The applications are deployed to separate Vercel projects but work together:

- Static Site: Deployed to `munconnect.org`
- Dashboard: Deployed to `dashboard.munconnect.org`

The static site is configured to redirect all `/dashboard/*` routes to the dashboard application.

## Development

Each project can be developed independently:

```bash
# For the static site
cd static-mun-connect
npm install
npm run dev

# For the dashboard application
cd dashboard-mun-connect
npm install
npm run dev
```

## Deployment

You can deploy both projects using the provided script:

```bash
./deploy-projects.sh
```

Or deploy them individually:

```bash
# For the static site
cd static-mun-connect
vercel --prod

# For the dashboard application
cd dashboard-mun-connect
vercel --prod
```

## Environment Variables

Make sure to set up the appropriate environment variables in each Vercel project:

### Dashboard Application
- `NEXT_PUBLIC_SUPABASE_URL`: Your Supabase project URL
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`: Your Supabase anonymous key

## Domain Configuration

In Vercel, configure:
- The static site to use `munconnect.org`
- The dashboard to use `dashboard.munconnect.org` 