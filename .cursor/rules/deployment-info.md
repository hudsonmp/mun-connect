# Deployment Environment Information

This document provides comprehensive details about the deployment environment for the Model UN Assistant platform, focusing on a streamlined and cost-effective setup.

## Environment Overview

The Model UN Assistant platform uses a modern, cloud-based architecture with these key components:

1. **Frontend**: Next.js app hosted on Vercel
2. **Backend**: Flask API hosted on Render
3. **Authentication & Storage**: Supabase
4. **Text Editor**: TinyMCE Cloud (Free Tier)
5. **AI Model**: OpenAI API (GPT-4o/3.5-Turbo)

## Development Environment

### Prerequisites

- **Python**: 3.10+ (3.11 recommended)
- **Node.js**: 18.x LTS
- **npm**: 9.x+
- **Git**: 2.x+
- **Operating System**: macOS, Windows, or Linux (Ubuntu 20.04+ recommended)

### Local Setup Instructions

1. **Backend Setup**:
   ```bash
   # Clone repository
   git clone https://github.com/yourusername/modelun-assistant.git
   cd modelun-assistant/backend
   
   # Create virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   
   # Install dependencies
   pip install -r requirements.txt
   
   # Set up environment variables
   cp .env.example .env  # Edit .env with your API keys
   
   # Run development server
   flask run --debug
   ```

2. **Frontend Setup**:
   ```bash
   cd ../frontend
   
   # Install dependencies
   npm install
   
   # Set up environment variables
   cp .env.example .env.local  # Edit with your API endpoints
   
   # Run development server
   npm run dev
   ```

3. **Access Local Environment**:
   - Backend API: http://localhost:5000
   - Frontend: http://localhost:3000

## Production Environment

### Backend (Render)

- **Service Type**: Web Service
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `gunicorn app:app`
- **Python Version**: 3.11
- **Instance Type**: Free tier (512MB RAM, 0.1 CPU)
  - Upgrade to "Starter" ($7/month) when user base grows
- **Environment Variables**:
  ```
  FLASK_ENV=production
  OPENAI_API_KEY=sk-...
  SUPABASE_URL=https://your-project.supabase.co
  SUPABASE_SERVICE_KEY=eyJ...
  TINYMCE_API_KEY=your-api-key
  RATE_LIMIT_PER_MINUTE=3
  RATE_LIMIT_PER_DAY=30
  ```

### Frontend (Vercel)

- **Framework Preset**: Next.js
- **Build Command**: `npm run build`
- **Output Directory**: `.next`
- **Node.js Version**: 18.x
- **Instance Type**: Hobby Plan (Free)
- **Environment Variables**:
  ```
  NEXT_PUBLIC_API_URL=https://your-backend.onrender.com
  NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
  NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...
  NEXT_PUBLIC_TINYMCE_API_KEY=your-api-key
  ```

### Supabase Configuration

- **Plan**: Free tier (up to 500MB database, 1GB storage)
- **Auth Settings**:
  - Enable Email/Password provider
  - Disable email confirmation (optional)
  - Set site URL to your frontend domain
- **Database**:
  - Run [migration.sql](path-to-migration-sql) to set up schema
  - Enable Row-Level Security (RLS) policies
- **Storage**:
  - Create `mun-files` bucket with RLS policies
  - Configure CORS to allow uploads from your domains

### TinyMCE Cloud

- **Plan**: Free tier (10,000 monthly editor initializations)
- **API Key**: Create at [TinyMCE Cloud Dashboard](https://www.tiny.cloud/auth/signup/)
- **Configuration**:
  ```js
  {
    height: 500,
    menubar: false,
    plugins: [
      'advlist', 'autolink', 'lists', 'link', 'charmap', 
      'searchreplace', 'wordcount'
    ],
    toolbar: 'bold italic | bullist numlist | link | removeformat'
  }
  ```

### OpenAI API

- **Plan**: Pay-as-you-go
- **Models**:
  - Development/Testing: `gpt-4o` (free tier)
  - Production: `gpt-3.5-turbo` (cost-effective for MVP)
- **Rate Limits**: Implemented in application code
- **Estimated Costs**:
  - Average tokens per position paper: ~2,500 tokens
  - Cost per position paper (gpt-3.5-turbo): ~$0.0075
  - Monthly cost (100 users, 10 papers each): ~$7.50

## Deployment Process

### Backend Deployment to Render

1. Connect GitHub repository to Render
2. Create new Web Service pointing to repository
3. Configure build settings and environment variables
4. Deploy from main branch

### Frontend Deployment to Vercel

1. Connect GitHub repository to Vercel
2. Configure project settings and environment variables
3. Deploy from main branch

### Continuous Integration/Deployment

- **Approach**: Deploy from main branch only
- **Testing**: Manual testing before merging to main
- **Rollback Strategy**: Revert to previous commit if issues arise

## Monitoring and Logs

### Backend Monitoring (Render)

- Access logs from Render dashboard
- Basic metrics included in free tier
- Custom logging to stdout/stderr

### Frontend Monitoring (Vercel)

- Deployment logs and basic analytics in Vercel dashboard
- Simple error tracking with custom error boundaries

### Database Monitoring (Supabase)

- Basic metrics in dashboard
- SQL query performance monitoring

## Scaling Considerations

- **Current Capacity**: ~100 concurrent users
- **Scaling Trigger Points**:
  - Backend: Upgrade to Render "Starter" plan when response times exceed 1 second
  - Database: Monitor Supabase usage, plan to upgrade if approaching 80% of limits
  - Storage: Set file size limits to prevent exceeding storage quota

## Backup Strategy

- **Database**: Rely on Supabase automated backups
- **Critical Code**: GitHub repository
- **User Documents**: Stored in Supabase with version history

## Security Measures

1. **Authentication**: JWT-based via Supabase
2. **API Security**:
   - CORS restrictions to allowed domains
   - Rate limiting to prevent abuse
   - Input validation on all endpoints
3. **Data Protection**:
   - Row-Level Security for database access
   - HTTPS for all communications
   - API keys stored as environment variables

## Troubleshooting Common Issues

### Backend Issues

1. **API Timeouts**:
   - Check Render logs for memory/CPU constraints
   - Verify OpenAI API is responding
   - Implement retry logic for transient failures

2. **Deployment Failures**:
   - Check build logs for dependency issues
   - Verify environment variables are set correctly

### Frontend Issues

1. **API Connection Errors**:
   - Verify API URL is correct
   - Check CORS configuration
   - Test API independently with curl/Postman

2. **Editor Loading Issues**:
   - Verify TinyMCE API key
   - Check browser console for errors
   - Test with minimal configuration

## Dependencies and Versions

### Backend Dependencies

```
Flask==2.3.3
gunicorn==21.2.0
openai==1.3.0
supabase==1.0.3
python-dotenv==1.0.0
flask-cors==4.0.0
flask-limiter==3.5.0
PyJWT==2.8.0
```

### Frontend Dependencies

```json
{
  "dependencies": {
    "next": "13.5.4",
    "react": "18.2.0",
    "react-dom": "18.2.0",
    "@supabase/supabase-js": "2.38.0",
    "@tinymce/tinymce-react": "4.3.0"
  },
  "devDependencies": {
    "eslint": "8.51.0",
    "eslint-config-next": "13.5.4"
  }
}
```

## Resource Requirements

### Minimum Requirements

- **Backend**: 512MB RAM, 0.1 CPU (Render Free tier)
- **Frontend**: Static hosting (Vercel Hobby plan)
- **Database**: 500MB (Supabase Free tier)
- **Storage**: 1GB (Supabase Free tier)
- **External APIs**: OpenAI API ($10-20/month for initial usage)

### Expected Load

- **Concurrent Users**: 10-20 during MVP phase
- **API Requests**: ~1,000 per day
- **Document Generations**: ~100 per day
- **Storage Growth**: ~10MB per day

### Cost Estimate ($10-20/month)

- **Render**: Free tier ($0)
- **Vercel**: Hobby plan ($0)
- **Supabase**: Free tier ($0)
- **TinyMCE**: Free tier ($0)
- **OpenAI API**: $10-20/month (estimated for 100 users)

## Maintenance Schedule

- **Frontend Updates**: Monthly
- **Backend Updates**: Monthly
- **Dependency Updates**: Quarterly
- **Database Optimization**: Quarterly

This deployment setup is designed to minimize costs while providing a robust platform capable of serving the MVP needs. The infrastructure can be easily scaled as user adoption grows.
