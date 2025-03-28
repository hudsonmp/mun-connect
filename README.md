# MUN Connect

MUN Connect is a platform for Model United Nations participants to manage their conferences, documents, and track their progress. This application uses Next.js for the frontend and Supabase with Python for the backend.

## Features

- User authentication (signup, login, password reset)
- Conference management
- Document management (position papers, resolutions, speeches)
- User statistics
- Dark/light mode support
- Responsive design

## Technology Stack

- **Frontend**: Next.js, React, TypeScript, Tailwind CSS
- **Backend**: Supabase, Python, Flask
- **Database**: PostgreSQL (via Supabase)
- **Authentication**: Supabase Auth

## Prerequisites

- Node.js (v18 or later)
- Python (v3.8 or later)
- Supabase CLI
- Local Supabase instance running

## Installation

1. Clone the repository:

```bash
git clone <repository-url>
cd mun-connect
```

2. Install Node.js dependencies:

```bash
npm install
```

3. Install Python dependencies:

```bash
cd backend
pip install -r requirements.txt
cd ..
```

4. Create a `.env` file in the root directory with the following variables:

```
NEXT_PUBLIC_SUPABASE_URL=http://localhost:54321
NEXT_PUBLIC_SUPABASE_ANON_KEY=<your-anon-key>
SUPABASE_SERVICE_ROLE_KEY=<your-service-role-key>
DATABASE_URL=postgresql://postgres:postgres@localhost:54322/postgres
```

## Setting Up the Database

Initialize the database schema and seed data:

```bash
npm run init-db
```

This will:
- Connect to your local Supabase instance
- Create the necessary tables (conferences, documents, user_stats)
- Set up Row Level Security policies
- Create functions and triggers
- Seed sample data for testing

## Running the Application

### Development

Run both the frontend and backend concurrently:

```bash
npm run dev:all
```

Or run them separately:

```bash
# Frontend only
npm run dev

# Backend only
npm run backend
```

### Production

Build the application:

```bash
npm run build
```

Start the production server:

```bash
npm run start
```

## Authentication Flow

1. Users can sign up with email and password
2. Email verification is handled by Supabase
3. Users can log in with their credentials
4. Session management is handled by our auth context

## Project Structure

```
mun-connect/
├── backend/          # Python backend code
│   ├── app.py        # Flask application
│   ├── db.py         # Supabase client and database operations
│   ├── schema.py     # Database schema definition
│   ├── init_db.sh    # Database initialization script
│   ├── run.sh        # Script to run the Flask server
│   └── requirements.txt  # Python dependencies
├── supabase/         # Supabase configuration
├── src/
│   ├── app/          # Next.js app router pages
│   │   ├── api/      # Next.js API routes
│   │   ├── auth/     # Authentication pages
│   │   └── page.tsx  # Main dashboard page
│   ├── components/   # React components
│   ├── lib/          # Utility functions and hooks
│   └── hooks/        # Custom React hooks
├── public/           # Static assets
└── package.json      # Node.js dependencies and scripts
```

## API Endpoints

### Authentication
- `POST /api/auth/signup` - Create a new user
- `POST /api/auth/signin` - Log in a user
- `POST /api/auth/signout` - Log out a user
- `POST /api/auth/reset-password` - Send a password reset link

### Conferences
- `GET /api/conferences` - Get all conferences for a user
- `POST /api/conferences` - Create a new conference
- `GET /api/conferences/:id` - Get a specific conference
- `PUT /api/conferences/:id` - Update a conference
- `DELETE /api/conferences/:id` - Delete a conference

### Documents
- `GET /api/documents` - Get all documents for a user
- `POST /api/documents` - Create a new document
- `GET /api/documents/:id` - Get a specific document
- `PUT /api/documents/:id` - Update a document
- `DELETE /api/documents/:id` - Delete a document

### User Stats
- `GET /api/user-stats` - Get user stats
- `PUT /api/user-stats/awards` - Update user awards count

## AI Features (Placeholders)

The application includes placeholders for AI features:
- `POST /api/ai/generate-document` - Generate a document using AI
- `POST /api/ai/improve-document` - Improve a document using AI

## License

[MIT](LICENSE)
