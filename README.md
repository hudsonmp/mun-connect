# MUN Connect

MUN Connect is a modern AI-powered Model UN platform targeting Gen Z users with research, writing, conference management, and networking features.

## Project Structure

This repository has been reorganized into two separate Next.js applications that are deployed independently on Vercel:

1. **Static Site** (`projects/static-mun-connect/`): Contains the landing page and public content
2. **Dashboard Application** (`projects/dashboard-mun-connect/`): Contains the authenticated dashboard and all app functionality

## Getting Started

To work with either project, navigate to its directory:

```bash
# For the static site
cd projects/static-mun-connect
npm install
npm run dev

# For the dashboard application
cd projects/dashboard-mun-connect
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
cd projects/static-mun-connect
vercel --prod

# For the dashboard application
cd projects/dashboard-mun-connect
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

## More Information

For more details about each project, see the README files in their respective directories:

- [Static Site README](./projects/static-mun-connect/README.md)
- [Dashboard Application README](./projects/dashboard-mun-connect/README.md)
- [Project Structure README](./projects/README.md) 