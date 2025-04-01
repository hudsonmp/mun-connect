# MVP Architecture Overview: Lean and Effective

## System Architecture

This document outlines the high-level architecture for the Model UN Assistant platform - an efficient, focused application that generates position papers, resolution papers, and speeches for Model UN delegates with minimal complexity and maximum effectiveness.

### Overview Diagram

```
┌─────────────────┐     ┌───────────────────┐      ┌──────────────────────┐
│                 │     │                   │      │                      │
│  React Frontend ├────►│  Flask Backend    ├─────►│  OpenAI API          │
│  (Vercel)       │     │  (Render)         │      │  (GPT-4o/3.5 Turbo)  │
│                 │     │                   │      │                      │
└────────┬────────┘     └─────────┬─────────┘      └──────────────────────┘
         │                        │
         │                        │
         ▼                        ▼
┌─────────────────┐     ┌───────────────────┐
│                 │     │                   │
│  TinyMCE Editor │     │  Supabase         │
│  (Free Tier)    │     │  (Auth & Storage) │
│                 │     │                   │
└─────────────────┘     └───────────────────┘
```

## Component Breakdown

### 1. Frontend (React/Next.js - Hosted on Vercel)
- **Ultra-Simple Chat Interface:** Clean, minimal interface inspired by Claude/ChatGPT with Model UN focus
- **TinyMCE Integration:** Free tier for document editing with essential formatting features only
- **No Dashboard by Default:** Optional access but not the primary flow
- **High School Student-Friendly Design:** Optimized for teenage users with limited AI experience
- **Guided Document Creation:** System asks targeted questions rather than requiring user prompting

### 2. Backend (Flask - Hosted on Render)
- **Lean API Layer:** Minimal, focused endpoints with clear responsibilities
- **Robust Error Handling:** Graceful fallbacks when non-critical components fail
- **Efficient Prompt Engineering:** Optimized prompts that maximize AI output quality while minimizing tokens
- **Rate Limiting:** Strict limits (3 requests/minute, 30/day per user) to control costs
- **Simple Document Processing:** Basic extraction of key information from reference materials

### 3. Database & Authentication (Supabase)
- **Streamlined Schema:** Only 3 essential tables (users, documents, reference_materials)
- **Simplified Authentication:** Email/password only for MVP with minimal profile information
- **Document Storage:** Basic version control with size limits (max 80 pages per document)
- **Reference Storage:** File size limits (5MB per file) and type restrictions (PDF, DOCX, TXT only)

### 4. AI Integration (OpenAI API)
- **GPT-4o Integration:** Using free tier for testing, GPT-3.5-Turbo for production to manage costs
- **Optimized Prompts:** Carefully crafted templates for each document type to minimize token usage
- **Fallback Strategies:** Graceful handling of API timeouts or failures

### 5. Deployment Strategy
- **Frontend:** Vercel for React application (free tier)
- **Backend:** Render for Flask backend (free tier)
- **Database/Auth/Storage:** Supabase (free tier)
- **Local Development:** Hot reloading with strict linting to prevent code bloat

## Critical System Flows

### 1. Document Generation Flow
```
User uploads materials → System asks targeted questions → 
Backend processes essential information → AI generates document → 
Document displayed in TinyMCE editor → User can edit → Save to Supabase
```

### 2. Authentication Flow
```
User signs up/logs in → Supabase handles auth → 
JWT passed to backend → Minimal user profile created → 
Access to document generation with rate limits applied
```

### 3. Document Storage & Retrieval
```
User saves document → Size-checked and stored in Supabase → 
Simple version tracking (max 3 versions) → 
One-click export to common formats (PDF, DOCX)
```

## Error Handling Strategy

1. **Graceful Degradation:** Core document generation works even if non-essential features fail
2. **Clear Error Messages:** User-friendly explanations without technical jargon
3. **Automatic Retry:** Single automatic retry for OpenAI API failures with fallback to shorter prompts
4. **State Preservation:** Document drafts saved locally to prevent work loss during failures
5. **Error Logging:** Capture errors without exposing details to users

## Testing Strategy

1. **Manual Testing First:** Founder-driven testing of core flows before adding automation
2. **Core Feature Focus:** Intensive testing of document generation quality with real Model UN scenarios
3. **Simple Integration Tests:** Basic route tests for critical API endpoints
4. **User Feedback Collection:** Simple thumbs up/down mechanism after document generation
5. **Document Quality Verification:** Manual review of generated content quality for initial users

## Code Quality Standards

1. **Minimal Codebase:** Maximum 2,000 lines of backend code, 3,000 lines of frontend code
2. **No Premature Optimization:** Only optimize what's proven to be a bottleneck
3. **Clear Function Responsibilities:** Each function does one thing well
4. **Limited Dependencies:** Only essential packages with clear purpose
5. **Self-Documenting Code:** Clear variable names and structure over excessive comments

## Development Priorities (Strict Order)

1. **Position Paper Generation:** Perfect this first before any other document type
2. **Ultra-Simple UI:** Chat interface optimized for high school students
3. **Basic Document Editor:** Minimal TinyMCE integration with essential formatting only
4. **Simple Auth:** Email/password only with minimal profile
5. **Basic File Upload:** Support for background guides and limited reference materials

This architecture embodies the "lean startup" approach with ruthless prioritization of the core value proposition, elimination of non-essential features, and focus on creating a delightful experience for high school Model UN delegates.
