-- Create committees table
CREATE TABLE IF NOT EXISTS committees (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  topic TEXT NOT NULL,
  description TEXT,
  conference_name TEXT NOT NULL,
  conference_date DATE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create documents table
CREATE TABLE IF NOT EXISTS documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title TEXT NOT NULL,
  content TEXT NOT NULL,
  document_type TEXT NOT NULL,
  tags TEXT[] DEFAULT '{}',
  is_public BOOLEAN DEFAULT FALSE,
  author_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
  committee_id UUID REFERENCES committees(id) ON DELETE SET NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create speeches table
CREATE TABLE IF NOT EXISTS speeches (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title TEXT NOT NULL,
  content TEXT NOT NULL,
  speech_type TEXT NOT NULL,
  duration_seconds INTEGER,
  tags TEXT[] DEFAULT '{}',
  is_public BOOLEAN DEFAULT FALSE,
  author_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
  committee_id UUID REFERENCES committees(id) ON DELETE SET NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create research_queries table
CREATE TABLE IF NOT EXISTS research_queries (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  query TEXT NOT NULL,
  result TEXT,
  status TEXT NOT NULL DEFAULT 'pending',
  model_used TEXT,
  user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
  committee_id UUID REFERENCES committees(id) ON DELETE SET NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable Row Level Security on all tables
ALTER TABLE committees ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE speeches ENABLE ROW LEVEL SECURITY;
ALTER TABLE research_queries ENABLE ROW LEVEL SECURITY;

-- Create policies for documents
CREATE POLICY "Users can view their own documents"
  ON documents FOR SELECT
  USING (auth.uid() = author_id);

CREATE POLICY "Users can view public documents"
  ON documents FOR SELECT
  USING (is_public = TRUE);

CREATE POLICY "Users can update their own documents"
  ON documents FOR UPDATE
  USING (auth.uid() = author_id);

CREATE POLICY "Users can delete their own documents"
  ON documents FOR DELETE
  USING (auth.uid() = author_id);

CREATE POLICY "Users can insert their own documents"
  ON documents FOR INSERT
  WITH CHECK (auth.uid() = author_id);

-- Create policies for speeches
CREATE POLICY "Users can view their own speeches"
  ON speeches FOR SELECT
  USING (auth.uid() = author_id);

CREATE POLICY "Users can view public speeches"
  ON speeches FOR SELECT
  USING (is_public = TRUE);

CREATE POLICY "Users can update their own speeches"
  ON speeches FOR UPDATE
  USING (auth.uid() = author_id);

CREATE POLICY "Users can delete their own speeches"
  ON speeches FOR DELETE
  USING (auth.uid() = author_id);

CREATE POLICY "Users can insert their own speeches"
  ON speeches FOR INSERT
  WITH CHECK (auth.uid() = author_id);

-- Create policies for research_queries
CREATE POLICY "Users can view their own research queries"
  ON research_queries FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can update their own research queries"
  ON research_queries FOR UPDATE
  USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own research queries"
  ON research_queries FOR DELETE
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own research queries"
  ON research_queries FOR INSERT
  WITH CHECK (auth.uid() = user_id);

-- Create policies for committees (public read, admin write)
CREATE POLICY "Anyone can view committees"
  ON committees FOR SELECT
  USING (TRUE);

CREATE POLICY "Admins can update committees"
  ON committees FOR UPDATE
  USING (
    EXISTS (
      SELECT 1 FROM profiles
      WHERE profiles.id = auth.uid()
      AND profiles.is_admin = TRUE
    )
  );

CREATE POLICY "Admins can delete committees"
  ON committees FOR DELETE
  USING (
    EXISTS (
      SELECT 1 FROM profiles
      WHERE profiles.id = auth.uid()
      AND profiles.is_admin = TRUE
    )
  );

CREATE POLICY "Admins can insert committees"
  ON committees FOR INSERT
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM profiles
      WHERE profiles.id = auth.uid()
      AND profiles.is_admin = TRUE
    )
  );

-- Create indexes
CREATE INDEX IF NOT EXISTS documents_author_id_idx ON documents (author_id);
CREATE INDEX IF NOT EXISTS documents_committee_id_idx ON documents (committee_id);
CREATE INDEX IF NOT EXISTS speeches_author_id_idx ON speeches (author_id);
CREATE INDEX IF NOT EXISTS speeches_committee_id_idx ON speeches (committee_id);
CREATE INDEX IF NOT EXISTS research_queries_user_id_idx ON research_queries (user_id);
CREATE INDEX IF NOT EXISTS research_queries_committee_id_idx ON research_queries (committee_id); 