# MUN Connect - Dashboard Application

This is the dashboard application for MUN Connect, containing all authenticated features and functionality.

## Features

- User authentication (login, registration)
- Dashboard with MUN-related tools
- Profile management
- Conference management
- Research tools
- Writing assistance
- Networking features

## Development

```bash
# Install dependencies
npm install

# Run development server
npm run dev
```

## Deployment

This project is configured to be deployed on Vercel. You can deploy it using:

```bash
vercel --prod
```

## Configuration

The application is configured with:

- Base path: `/dashboard`
- Authentication via Supabase
- Protected routes for authenticated users

## Environment Variables

The following environment variables need to be set in your Vercel project:

- `NEXT_PUBLIC_SUPABASE_URL`: Your Supabase project URL
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`: Your Supabase anonymous key 