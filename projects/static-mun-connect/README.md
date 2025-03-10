# MUN Connect - Static Site

This is the static site for MUN Connect, containing the landing page and public content.

## Features

- Landing page with information about MUN Connect
- Links to the dashboard application for login/registration
- Public information pages

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

The site is configured to redirect `/dashboard/*` routes to the dashboard application hosted at `dashboard.munconnect.org`. 