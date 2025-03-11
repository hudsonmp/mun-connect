-- Add missing columns to profiles table
ALTER TABLE profiles 
ADD COLUMN IF NOT EXISTS country TEXT,
ADD COLUMN IF NOT EXISTS school TEXT,
ADD COLUMN IF NOT EXISTS education_level TEXT CHECK (education_level IS NULL OR education_level IN ('middle_school', 'high_school', 'university', 'other')),
ADD COLUMN IF NOT EXISTS interests TEXT[],
ADD COLUMN IF NOT EXISTS conference_experience TEXT[]; 