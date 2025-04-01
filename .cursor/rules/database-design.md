# Simplified Database Design Document

## Overview

This document outlines the minimalist database structure for the Model UN Assistant platform using Supabase. The design ruthlessly prioritizes simplicity while providing only the essential functionality for the MVP, focusing on user authentication, document storage, and reference material management.

## Database Technology

**Supabase**: Selected for its free tier offering authentication, PostgreSQL database, and storage in a single platform.

## Simplified Schema Design

### Database Tables

We limit our schema to just 3 essential tables:

#### 1. Users Table (`auth.users`)

Leverages Supabase's built-in auth.users table with minimal customization:

| Column | Type | Description |
|--------|------|-------------|
| id | uuid | Primary key, automatically generated |
| email | varchar | User's email address |
| encrypted_password | varchar | Securely stored password |
| created_at | timestamp | Account creation time |
| last_sign_in_at | timestamp | Last login timestamp |

> Note: We're using only the essential fields from Supabase's auth system.

#### 2. User Profiles (`profiles`)

Minimal extension of user information:

| Column | Type | Description | Constraints |
|--------|------|-------------|-------------|
| id | uuid | Primary key | References auth.users(id) |
| display_name | varchar | User's display name | Not null |
| created_at | timestamp | Record creation time | Default: now() |

```sql
CREATE TABLE profiles (
  id UUID REFERENCES auth.users(id) PRIMARY KEY,
  display_name VARCHAR NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Simple trigger to create profile on user creation
CREATE FUNCTION public.handle_new_user() 
RETURNS TRIGGER AS $
BEGIN
  INSERT INTO public.profiles (id, display_name)
  VALUES (new.id, split_part(new.email, '@', 1));
  RETURN new;
END;
$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();
```

#### 3. Documents (`documents`)

Streamlined document storage with essential metadata:

| Column | Type | Description | Constraints |
|--------|------|-------------|-------------|
| id | uuid | Primary key | Default: uuid_generate_v4() |
| user_id | uuid | Owner of the document | References auth.users(id) |
| title | varchar | Document title | Not null |
| document_type | varchar | Type of document | Enum: 'position_paper', 'resolution', 'speech' |
| content | text | Document content in HTML | Not null, max 250KB |
| committee | varchar | Model UN committee | Not null, max 100 chars |
| country | varchar | Represented country | Not null, max 100 chars |
| topic | varchar | Document topic | Not null, max 250 chars |
| reference_paths | jsonb | Array of storage paths | Default: '[]' |
| version | integer | Document version | Default: 1 |
| created_at | timestamp | Creation timestamp | Default: now() |
| updated_at | timestamp | Last update | Default: now() |

```sql
CREATE TABLE documents (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES auth.users(id) NOT NULL,
  title VARCHAR(150) NOT NULL,
  document_type VARCHAR(20) CHECK (document_type IN ('position_paper', 'resolution', 'speech')) NOT NULL,
  content TEXT NOT NULL CHECK (LENGTH(content) <= 256000),
  committee VARCHAR(100) NOT NULL,
  country VARCHAR(100) NOT NULL,
  topic VARCHAR(250) NOT NULL,
  reference_paths JSONB DEFAULT '[]',
  version INTEGER DEFAULT 1,
  created_at

  TIMESTAMP WITH TIME ZONE DEFAULT now(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Only the most essential indexes
CREATE INDEX idx_documents_user_id ON documents(user_id);
CREATE INDEX idx_documents_type ON documents(document_type);
```

#### 4. Reference Materials Storage

Instead of a dedicated table, we'll use Supabase Storage directly with a structured path convention:

- Storage path format: `users/{user_id}/{document_id}/{file_name}`
- File size limit: 5MB per file
- Allowed file types: PDF, DOCX, TXT only
- Metadata stored in the documents table under reference_paths JSON field

## Storage Buckets

We'll use a single Storage bucket to keep things simple:

### Document Storage Bucket (`mun-files`)
- Stores all user files: both reference materials and exported documents
- Access rules:
  - Users can only read/write their own files
  - Files automatically expire after 30 days if marked as temporary

## Row-Level Security (RLS) Policies

Implementing minimal RLS policies to ensure users can only access their own data:

### Profiles Table
```sql
-- Allow users to read/update only their own profile
CREATE POLICY profiles_select_own ON profiles FOR SELECT 
  USING (id = auth.uid());

CREATE POLICY profiles_update_own ON profiles FOR UPDATE 
  USING (id = auth.uid());
```

### Documents Table
```sql
-- Allow users to CRUD only their own documents
CREATE POLICY documents_select_own ON documents FOR SELECT 
  USING (user_id = auth.uid());

CREATE POLICY documents_insert_own ON documents FOR INSERT 
  WITH CHECK (user_id = auth.uid());

CREATE POLICY documents_update_own ON documents FOR UPDATE 
  USING (user_id = auth.uid());

CREATE POLICY documents_delete_own ON documents FOR DELETE 
  USING (user_id = auth.uid());
```

## Document Versioning

To support TinyMCE document editing with version control:

1. When a document is first created:
   - Set version = 1
   - Store content in the documents table

2. When a document is updated:
   - Increment version number
   - Update content and updated_at timestamp
   - If version > 3, delete oldest version (we only keep last 3 versions)

3. To retrieve a specific version:
   - Use built-in Supabase PostgreSQL "temporal tables" pattern for versioning

```sql
-- Simplified version history implementation
CREATE OR REPLACE FUNCTION document_version_history() RETURNS TRIGGER AS $
BEGIN
  -- Store the previous version in a JSON field
  IF TG_OP = 'UPDATE' THEN
    UPDATE documents 
    SET metadata = jsonb_set(
      COALESCE(metadata, '{}'::jsonb),
      '{versions}',
      COALESCE(metadata->'versions', '[]'::jsonb) || 
      jsonb_build_object('version', OLD.version, 'content', OLD.content, 'updated_at', OLD.updated_at)
    )
    WHERE id = NEW.id;
    
    -- Only keep last 3 versions
    UPDATE documents
    SET metadata = jsonb_set(
      metadata,
      '{versions}',
      (SELECT jsonb_agg(x) FROM (
        SELECT x FROM jsonb_array_elements(metadata->'versions') x
        ORDER BY (x->>'updated_at')::timestamp DESC
        LIMIT 3
      ) t)
    )
    WHERE id = NEW.id;
  END IF;
  
  RETURN NEW;
END;
$ LANGUAGE plpgsql;

CREATE TRIGGER document_version_history_trigger
BEFORE UPDATE ON documents
FOR EACH ROW
WHEN (OLD.content IS DISTINCT FROM NEW.content)
EXECUTE FUNCTION document_version_history();
```

## Performance Considerations

1. **Minimal Indexes**: Only adding indexes for frequent query patterns
2. **JSON for Flexibility**: Using JSON for version history and reference paths
3. **Size Limits**: Enforcing size limits to prevent performance issues
4. **Row-Level Security**: Using Supabase RLS for data isolation

## Backup Strategy

1. **Automated Backups**: Relying on Supabase's automated backups
2. **Export Option**: Adding a admin-only export function for critical data backup

This streamlined database design provides just enough functionality for the MVP while maintaining simplicity and performance.
