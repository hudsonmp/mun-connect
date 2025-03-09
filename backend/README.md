# MUN Connect Backend

A simplified Flask backend for MUN Connect, focusing only on authentication and profile management.

## Features

- User authentication (register, login, refresh tokens)
- Profile management (create, read, update)

## Tech Stack

- **Framework**: Flask with Blueprints
- **ORM**: Flask-SQLAlchemy
- **Authentication**: Flask-JWT-Extended
- **Database**: PostgreSQL via Supabase

## Getting Started

### Prerequisites

- Python 3.9+
- Supabase account

### Installation

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set up environment variables:
   ```bash
   export FLASK_APP=run.py
   export FLASK_ENV=development
   ```

3. Run the development server:
   ```bash
   flask run
   ```

## API Endpoints

### Authentication

- `POST /api/auth/register` - Register a new user
- `POST /api/auth/login` - Login and get access token
- `POST /api/auth/refresh` - Refresh access token

### Profile Management

- `GET /api/users/profile` - Get current user's profile
- `PUT /api/users/profile` - Update current user's profile 