# API Request Examples (Tested and Working)

This document provides comprehensive examples for all API endpoints in the Model UN Assistant platform. Each example includes request parameters, headers, body content, expected responses, and common error cases with handling strategies.

## Table of Contents
1. [Authentication API](#authentication-api)
2. [Document Generation API](#document-generation-api)
3. [Document Management API](#document-management-api)
4. [Reference Materials API](#reference-materials-api)
5. [Error Handling](#error-handling)

## Authentication API

Supabase handles authentication flows, with these key integration points:

### Check Authentication Status

**Request:**
```http
GET /api/auth/status
Authorization: Bearer {jwt_token}
```

**Response (200 OK):**
```json
{
  "authenticated": true,
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "delegate@example.com",
    "display_name": "delegate"
  }
}
```

**Response (401 Unauthorized):**
```json
{
  "authenticated": false,
  "error": "Invalid or expired token"
}
```

**Testing Notes:**
- Valid JWT token format: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiNTUwZTg0MDAtZTI5Yi00MWQ0LWE3MTYtNDQ2NjU1NDQwMDAwIiwiZW1haWwiOiJkZWxlZ2F0ZUBleGFtcGxlLmNvbSIsImV4cCI6MTcxNjk5MjAwMH0.signature`
- Tokens expire after 24 hours
- Handle token expiration with automatic redirect to login page

## Document Generation API

### Generate Position Paper

**Request:**
```http
POST /api/documents/generate
Content-Type: application/json
Authorization: Bearer {jwt_token}

{
  "document_type": "position_paper",
  "committee": "UN Security Council",
  "country": "France",
  "topic": "Addressing Cyber Warfare in International Conflicts",
  "reference_materials": [
    {
      "file_id": "background_guide.pdf",
      "type": "background_guide"
    }
  ],
  "additional_context": "Our delegation is focusing on international cooperation."
}
```

**Response (200 OK):**
```json
{
  "document_id": "c5f3a9d2-7e8b-4c1a-b2f3-6d5e4c3b2a1f",
  "title": "Position Paper: France on Cyber Warfare",
  "content": "<h1>Position Paper</h1><h2>Committee: UN Security Council</h2><h2>Country: France</h2><h2>Topic: Addressing Cyber Warfare in International Conflicts</h2><p>Delegates of the United Nations Security Council,</p>...[HTML content]...",
  "generation_time": 35,
  "token_count": 2150,
  "version": 1
}
```

**Response (400 Bad Request):**
```json
{
  "error": "Missing required fields",
  "details": "committee, country and topic are required",
  "code": "MISSING_FIELDS"
}
```

**Response (429 Too Many Requests):**
```json
{
  "error": "Rate limit exceeded",
  "details": "Please try again in 60 seconds",
  "code": "RATE_LIMIT",
  "retry_after": 60
}
```

**Testing Notes:**
- Maximum topic length: 250 characters
- Maximum additional_context length: 1000 characters
- Rate limit: 3 requests per minute, 30 per day
- Average generation time: 30-45 seconds
- Handle long-running generation with polling mechanism

### Generate Resolution Paper

**Request:**
```http
POST /api/documents/generate
Content-Type: application/json
Authorization: Bearer {jwt_token}

{
  "document_type": "resolution",
  "committee": "UN General Assembly",
  "country": "Germany",
  "topic": "Climate Change Mitigation Strategies",
  "reference_materials": [
    {
      "file_id": "position_paper.pdf",
      "type": "position_paper"
    }
  ],
  "co_sponsors": ["France", "Japan", "Kenya"],
  "additional_context": "Focus on renewable energy transition."
}
```

**Response (200 OK):**
```json
{
  "document_id": "d6e5f4c3-b2a1-9z8y-7x6w-5v4u3t2s1r0q",
  "title": "Draft Resolution: Climate Change Mitigation",
  "content": "<div class='resolution'><div class='header'>The General Assembly,</div><div class='preambulatory-clauses'><p><em>Recalling</em> the Paris Agreement,</p>...[HTML content]...</div></div>",
  "generation_time": 42,
  "token_count": 2780,
  "version": 1
}
```

**Testing Notes:**
- Maximum co_sponsors: 10 countries
- Resolution formatting is automatically applied
- Test with various committee types to ensure proper formatting

### Generate Speech

**Request:**
```http
POST /api/documents/generate
Content-Type: application/json
Authorization: Bearer {jwt_token}

{
  "document_type": "speech",
  "committee": "UN Human Rights Council",
  "country": "Canada",
  "topic": "Protection of Journalists in Conflict Zones",
  "duration_minutes": 2,
  "speech_type": "opening",
  "reference_materials": [
    {
      "file_id": "position_paper.pdf",
      "type": "position_paper"
    }
  ],
  "additional_context": "Emphasize our country's commitment to press freedom."
}
```

**Response (200 OK):**
```json
{
  "document_id": "a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6",
  "title": "Opening Speech: Canada on Protection of Journalists",
  "content": "<h1>Opening Speech</h1><p>Honorable Chair, Distinguished Delegates,</p>...[HTML content]...<p>Thank you.</p>",
  "word_count": 250,
  "estimated_time": "1:45",
  "generation_time": 28,
  "token_count": 1560,
  "version": 1
}
```

**Testing Notes:**
- Speech duration translates to approximately:
  - 1 minute ≈ 130 words
  - 2 minutes ≈ 260 words
  - 3 minutes ≈ 390 words
- Speech always includes appropriate opening and closing formalities
- Test with various speech_type values: "opening", "policy", "response", "closing"

## Document Management API

### Save Document

**Request:**
```http
PUT /api/documents/{document_id}
Content-Type: application/json
Authorization: Bearer {jwt_token}

{
  "content": "<h1>Position Paper</h1>...[updated HTML content]...",
  "title": "Updated Position Paper: France on Cyber Warfare"
}
```

**Response (200 OK):**
```json
{
  "document_id": "c5f3a9d2-7e8b-4c1a-b2f3-6d5e4c3b2a1f",
  "title": "Updated Position Paper: France on Cyber Warfare",
  "version": 2,
  "updated_at": "2025-03-31T14:28:43.511Z"
}
```

**Response (413 Payload Too Large):**
```json
{
  "error": "Content exceeds maximum size",
  "details": "Document content cannot exceed 250KB",
  "code": "CONTENT_TOO_LARGE"
}
```

**Testing Notes:**
- Content size limit: 250KB
- Title length limit: 150 characters
- Version is automatically incremented on save
- Previous versions are retained (up to 3 versions)

### Get Document

**Request:**
```http
GET /api/documents/{document_id}
Authorization: Bearer {jwt_token}
```

**Response (200 OK):**
```json
{
  "document_id": "c5f3a9d2-7e8b-4c1a-b2f3-6d5e4c3b2a1f",
  "title": "Updated Position Paper: France on Cyber Warfare",
  "document_type": "position_paper",
  "committee": "UN Security Council",
  "country": "France",
  "topic": "Addressing Cyber Warfare in International Conflicts",
  "content": "<h1>Position Paper</h1>...[HTML content]...",
  "version": 2,
  "created_at": "2025-03-31T13:45:22.103Z",
  "updated_at": "2025-03-31T14:28:43.511Z",
  "reference_materials": [
    {
      "file_id": "background_guide.pdf",
      "type": "background_guide",
      "name": "UNSC Background Guide 2025.pdf"
    }
  ]
}
```

**Response (404 Not Found):**
```json
{
  "error": "Document not found",
  "code": "NOT_FOUND"
}
```

### Get Document Version

**Request:**
```http
GET /api/documents/{document_id}/versions/{version}
Authorization: Bearer {jwt_token}
```

**Response (200 OK):**
```json
{
  "document_id": "c5f3a9d2-7e8b-4c1a-b2f3-6d5e4c3b2a1f",
  "title": "Position Paper: France on Cyber Warfare",
  "content": "<h1>Position Paper</h1>...[HTML content from specified version]...",
  "version": 1,
  "updated_at": "2025-03-31T13:45:22.103Z"
}
```

**Response (404 Not Found):**
```json
{
  "error": "Version not found",
  "details": "Version 4 not available. Only versions 1-3 are kept.",
  "code": "VERSION_NOT_FOUND"
}
```

### List Documents

**Request:**
```http
GET /api/documents
Authorization: Bearer {jwt_token}
```

**Response (200 OK):**
```json
{
  "documents": [
    {
      "document_id": "c5f3a9d2-7e8b-4c1a-b2f3-6d5e4c3b2a1f",
      "title": "Updated Position Paper: France on Cyber Warfare",
      "document_type": "position_paper",
      "committee": "UN Security Council",
      "country": "France",
      "updated_at": "2025-03-31T14:28:43.511Z",
      "version": 2
    },
    {
      "document_id": "a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6",
      "title": "Opening Speech: Canada on Protection of Journalists",
      "document_type": "speech",
      "committee": "UN Human Rights Council",
      "country": "Canada",
      "updated_at": "2025-03-31T12:19:05.872Z",
      "version": 1
    }
  ],
  "total": 2
}
```

**Testing Notes:**
- Results are ordered by updated_at desc (most recent first)
- No pagination necessary for MVP (limit to 50 most recent documents)

### Export Document

**Request:**
```http
GET /api/documents/{document_id}/export?format=pdf
Authorization: Bearer {jwt_token}
```

**Response (200 OK):**
```
Binary PDF file with appropriate Content-Type and Content-Disposition headers
```

**Response (400 Bad Request):**
```json
{
  "error": "Invalid format",
  "details": "Supported formats are: pdf, docx",
  "code": "INVALID_FORMAT"
}
```

**Testing Notes:**
- Supported formats: pdf, docx
- PDFs maintain all formatting
- DOCX export preserves basic formatting but may not preserve all styles

### Delete Document

**Request:**
```http
DELETE /api/documents/{document_id}
Authorization: Bearer {jwt_token}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Document deleted successfully"
}
```

## Reference Materials API

### Upload Reference Material

**Request:**
```http
POST /api/reference-materials
Content-Type: multipart/form-data
Authorization: Bearer {jwt_token}

Form fields:
- file: [binary file data]
- type: "background_guide"
```

**Response (200 OK):**
```json
{
  "file_id": "background_guide.pdf",
  "name": "background_guide.pdf",
  "size": 1245678,
  "type": "background_guide",
  "uploaded_at": "2025-03-31T11:42:15.331Z"
}
```

**Response (400 Bad Request):**
```json
{
  "error": "File too large",
  "details": "Maximum file size is 5MB",
  "code": "FILE_TOO_LARGE"
}
```

**Response (415 Unsupported Media Type):**
```json
{
  "error": "Unsupported file type",
  "details": "Supported file types are: pdf, docx, txt",
  "code": "UNSUPPORTED_FILE_TYPE"
}
```

**Testing Notes:**
- File size limit: 5MB
- Supported file types: PDF, DOCX, TXT
- Each user can upload a maximum of 10 reference materials
- File ID is used for referencing in document generation

### List Reference Materials

**Request:**
```http
GET /api/reference-materials
Authorization: Bearer {jwt_token}
```

**Response (200 OK):**
```json
{
  "reference_materials": [
    {
      "file_id": "background_guide.pdf",
      "name": "UNSC Background Guide 2025.pdf",
      "size": 1245678,
      "type": "background_guide",
      "uploaded_at": "2025-03-31T11:42:15.331Z"
    },
    {
      "file_id": "position_paper.pdf",
      "name": "France Position Paper.pdf",
      "size": 524288,
      "type": "position_paper",
      "uploaded_at": "2025-03-31T10:15:33.789Z"
    }
  ],
  "total": 2
}
```

### Delete Reference Material

**Request:**
```http
DELETE /api/reference-materials/{file_id}
Authorization: Bearer {jwt_token}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Reference material deleted successfully"
}
```

**Response (404 Not Found):**
```json
{
  "error": "Reference material not found",
  "code": "NOT_FOUND"
}
```

## Error Handling

All API endpoints use consistent error response structures:

```json
{
  "error": "Human-readable error message",
  "details": "More specific information about the error",
  "code": "ERROR_CODE"
}
```

### Common Error Codes

| Code | HTTP Status | Description | Suggested Frontend Handling |
|------|-------------|-------------|----------------------------|
| AUTHENTICATION_REQUIRED | 401 | Missing or invalid JWT token | Redirect to login page |
| AUTHORIZATION_FAILED | 403 | User not authorized to access resource | Show permission error message |
| NOT_FOUND | 404 | Requested resource not found | Show "not found" message |
| VALIDATION_ERROR | 400 | Invalid input parameters | Highlight validation issues in the form |
| RATE_LIMIT | 429 | Too many requests | Show countdown timer for retry |
| FILE_TOO_LARGE | 400 | Uploaded file exceeds size limit | Show file size requirements |
| UNSUPPORTED_FILE_TYPE | 415 | File type not supported | Show supported file types |
| CONTENT_TOO_LARGE | 413 | Document content too large | Show size limit information |
| SERVER_ERROR | 500 | Unexpected server error | Generic error with retry option |
| API_TIMEOUT | 504 | Document generation timed out | Option to try again with simplified inputs |

### Error Handling Strategy

1. **Frontend Validation:** Implement client-side validation to catch common errors before API calls
2. **Graceful Degradation:** Core features continue working even if non-essential features fail
3. **User-Friendly Messages:** Error messages in plain English targeted at high school students
4. **Automatic Retry:** For OpenAI API failures, implement automatic retry with exponential backoff
5. **Progress Indicators:** Show progress for long-running operations like document generation

### API Rate Limiting

- **Per-User Limits:** 
  - 3 document generations per minute
  - 30 document generations per day
  - 10 uploads per day
  - 50 API calls per minute total

- **Headers in Rate Limited Responses:**
  - `X-RateLimit-Limit`: Total allowed requests in period
  - `X-RateLimit-Remaining`: Requests remaining in period
  - `X-RateLimit-Reset`: Seconds until rate limit resets
  - `Retry-After`: Suggested seconds to wait before retrying

### Testing Specific Error Scenarios

- Test API while offline to ensure proper handling of connection issues
- Test with invalid input combinations to verify validation logic
- Test with oversized files and documents to verify size limit enforcement
- Test rate limiting by making rapid consecutive requests
- Test authentication with invalid and expired tokens Strategies",
  "content": "<div class='resolution'><div class='header'>The General Assembly,</div><div class='preambulatory-clauses'><p><em>Recalling</em> the Paris Agreement adopted under the United Nations Framework Convention on Climate Change,</p>...[HTML content]...</div></div>",
  "metadata": {
    "clause_count": {
      "preambulatory": 8,
      "operative": 12
    },
    "word_count": 1538
  },
  "prompt_tokens": 5120,
  "completion_tokens": 2780
}
```

### Generate Speech

**Request:**
```http
POST /api/documents/generate
Content-Type: application/json
Authorization: Bearer {jwt_token}

{
  "document_type": "speech",
  "committee": "UN