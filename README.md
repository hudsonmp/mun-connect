# MUN Connect

MUN Connect is an AI-powered platform for Model UN participants, helping them prepare, research, and connect with other delegates.

## Project Setup

### Database Setup

The project uses Supabase as the database with the following setup:

1. **Profiles Table**: Stores user profile information
   - `id`: UUID (Primary key, references auth.users)
   - `username`: Text (Unique, Not Null)
   - `full_name`: Text
   - `bio`: Text
   - `avatar_url`: Text
   - `created_at`: Timestamp with timezone (Default: now())
   - `updated_at`: Timestamp with timezone (Default: now())

2. **Security Features**:
   - Row Level Security (RLS) enabled on the profiles table
   - Policies to ensure users can only view, update, and insert their own profiles
   - Automatic updating of the `updated_at` field via a trigger

### Development

1. **Prerequisites**:
   - Node.js (>= 18.0.0)
   - npm (>= 10.2.4)
   - Supabase account

2. **Setup**:
   ```bash
   npm install
   ```

3. **Run Development Server**:
   ```bash
   npm run dev
   # or
   npx vercel dev
   ```

4. **Build for Production**:
   ```bash
   npm run build
   ```

## Frontend Structure

The project uses Next.js 14+ with the App Router, TypeScript, and Shadcn UI components.

## Authentication

Authentication is managed through Supabase, with a custom user profiles system that integrates with Supabase Auth.

## Development Guidelines

- Follow Next.js best practices
- Use TypeScript for type safety
- Implement proper error handling
- Follow mobile-first responsive design principles 