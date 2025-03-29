# MUN Connect

A comprehensive platform for Model United Nations participants to manage conferences, create position papers, speeches, and resolutions.

## Features

- **Conference Management**: Keep track of upcoming, active, and past MUN conferences
- **Document Creation**: Generate and edit position papers, speeches, and resolutions
- **AI-Powered Assistance**: Generate position papers tailored to your committee and country
- **Research Tools**: Research countries, topics, and committees
- **Profile Management**: Track your MUN achievements and awards

## Tech Stack

- **Frontend**: Next.js, React, TypeScript, Tailwind CSS, shadcn/ui
- **Backend**: Flask (Python), OpenAI API
- **Database**: PostgreSQL (via Supabase)
- **Authentication**: Supabase Auth
- **Rich Text Editing**: TinyMCE

## Setup Instructions

### Prerequisites

- Node.js 18+ 
- Python 3.10+
- Supabase account
- OpenAI API key
- TinyMCE API key

### Environment Setup

1. Clone the repository
2. Create a `.env` file in the root directory with the following variables:

```
# Supabase
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key

# OpenAI
OPENAI_API_KEY=your_openai_api_key

# TinyMCE
NEXT_PUBLIC_TINYMCE_KEY=your_tinymce_key

# Database direct connection (for migrations)
DATABASE_URL=your_postgres_connection_string
```

### Installation

1. Install frontend dependencies:
```bash
npm install
```

2. Install backend dependencies:
```bash
cd backend
pip install -r requirements.txt
```

3. Initialize the database:
```bash
npm run init-db
```

### Development

Run both frontend and backend servers:
```bash
npm run dev:all
```

Or separately:
```bash
# Frontend only
npm run dev

# Backend only
npm run backend
```

## Usage

1. Register a new account
2. Add your MUN conferences
3. Create position papers, resolutions, or speeches
4. Use the AI assistant to generate content
5. Track your progress and achievements

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
