# Supabase Setup for MUN Connect

This directory contains SQL migrations for setting up the Supabase database for MUN Connect.

## Setup Instructions

1. Log in to your Supabase dashboard at https://app.supabase.com/
2. Select your project
3. Go to the SQL Editor
4. Create a new query
5. Copy and paste the contents of `migrations/create_profiles_table.sql` into the query editor
6. Run the query
7. Create another new query
8. Copy and paste the contents of `migrations/create_other_tables.sql` into the query editor
9. Run the query

## Table Structure

### Profiles

The `profiles` table stores user profile information:

- `id`: UUID (primary key, linked to auth.users)
- `username`: TEXT (unique)
- `full_name`: TEXT
- `bio`: TEXT
- `avatar_url`: TEXT
- `country`: TEXT
- `interests`: TEXT[]
- `conference_experience`: TEXT[]
- `is_admin`: BOOLEAN
- `created_at`: TIMESTAMP
- `updated_at`: TIMESTAMP

### Committees

The `committees` table stores information about Model UN committees:

- `id`: UUID (primary key)
- `name`: TEXT
- `topic`: TEXT
- `description`: TEXT
- `conference_name`: TEXT
- `conference_date`: DATE
- `created_at`: TIMESTAMP
- `updated_at`: TIMESTAMP

### Documents

The `documents` table stores user documents:

- `id`: UUID (primary key)
- `title`: TEXT
- `content`: TEXT
- `document_type`: TEXT
- `tags`: TEXT[]
- `is_public`: BOOLEAN
- `author_id`: UUID (foreign key to profiles)
- `committee_id`: UUID (foreign key to committees)
- `created_at`: TIMESTAMP
- `updated_at`: TIMESTAMP

### Speeches

The `speeches` table stores user speeches:

- `id`: UUID (primary key)
- `title`: TEXT
- `content`: TEXT
- `speech_type`: TEXT
- `duration_seconds`: INTEGER
- `tags`: TEXT[]
- `is_public`: BOOLEAN
- `author_id`: UUID (foreign key to profiles)
- `committee_id`: UUID (foreign key to committees)
- `created_at`: TIMESTAMP
- `updated_at`: TIMESTAMP

### Research Queries

The `research_queries` table stores AI research queries:

- `id`: UUID (primary key)
- `query`: TEXT
- `result`: TEXT
- `status`: TEXT
- `model_used`: TEXT
- `user_id`: UUID (foreign key to profiles)
- `committee_id`: UUID (foreign key to committees)
- `created_at`: TIMESTAMP
- `updated_at`: TIMESTAMP

## Row Level Security

All tables have Row Level Security (RLS) enabled with appropriate policies:

- Profiles: Users can only view and edit their own profiles
- Documents: Users can view and edit their own documents, and view public documents
- Speeches: Users can view and edit their own speeches, and view public speeches
- Research Queries: Users can view and edit their own research queries
- Committees: Anyone can view committees, but only admins can create, update, or delete them

## Triggers

A trigger is set up to automatically create a profile when a new user signs up through Supabase Auth. 