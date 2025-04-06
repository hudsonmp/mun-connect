-- Style Dimensions table
CREATE TABLE style_dimensions (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Questions Pool (predefined sentence pairs)
CREATE TABLE question_pool (
  id SERIAL PRIMARY KEY,
  question_external_id TEXT UNIQUE NOT NULL,
  sentence_a_id TEXT NOT NULL,
  sentence_b_id TEXT NOT NULL,
  sentence_a TEXT NOT NULL,
  sentence_b TEXT NOT NULL,
  dimension_tags TEXT[] NOT NULL,
  is_initial BOOLEAN DEFAULT FALSE,
  question_order INTEGER,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Assessment Sessions
CREATE TABLE style_assessment_sessions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES auth.users(id),
  document_type TEXT NOT NULL,
  completed BOOLEAN DEFAULT FALSE,
  response_count INTEGER DEFAULT 0,
  used_question_ids TEXT[] DEFAULT '{}',
  latest_beliefs JSONB DEFAULT '{}',
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  completed_at TIMESTAMP WITH TIME ZONE
);

-- User Responses to questions
CREATE TABLE style_assessment_responses (
  id SERIAL PRIMARY KEY,
  session_id UUID REFERENCES style_assessment_sessions(id),
  question_id TEXT NOT NULL,
  sentence_a_id TEXT NOT NULL,
  sentence_b_id TEXT NOT NULL,
  chosen_id TEXT NOT NULL,
  response_time_ms INTEGER,
  beliefs_after JSONB,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- User Style Profiles (final results)
CREATE TABLE user_style_profiles (
  id SERIAL PRIMARY KEY,
  user_id UUID REFERENCES auth.users(id) NOT NULL,
  document_type TEXT NOT NULL,
  dimension_values JSONB NOT NULL,
  confidence_scores JSONB NOT NULL,
  main_style_cluster TEXT,
  style_labels JSONB,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  UNIQUE(user_id, document_type)
);

-- Sentence Embeddings Cache
CREATE TABLE sentence_embeddings (
  id SERIAL PRIMARY KEY,
  sentence_id TEXT UNIQUE NOT NULL,
  embedding VECTOR(768),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Initialize style dimensions
INSERT INTO style_dimensions (name, description) VALUES
('formality', 'Level of formal language and academic tone'),
('technicality', 'Use of technical terminology and complex concepts'),
('persuasiveness', 'Degree of persuasive rhetoric and emotional appeal'),
('structure', 'Organization and logical flow of arguments'),
('diplomatic_tone', 'Level of diplomatic language and political sensitivity');

-- Create indexes for performance
CREATE INDEX idx_session_user ON style_assessment_sessions(user_id);
CREATE INDEX idx_response_session ON style_assessment_responses(session_id);
CREATE INDEX idx_style_profile_user ON user_style_profiles(user_id);