-- Add new columns to profiles table
ALTER TABLE profiles 
ADD COLUMN IF NOT EXISTS school TEXT,
ADD COLUMN IF NOT EXISTS education_level TEXT,
ADD COLUMN IF NOT EXISTS conference_experience TEXT[] DEFAULT '{}',
ADD COLUMN IF NOT EXISTS interests TEXT[] DEFAULT '{}';

-- Comment on columns for documentation
COMMENT ON COLUMN profiles.school IS 'User''s school or institution';
COMMENT ON COLUMN profiles.education_level IS 'User''s education level (middle_school, high_school, university, other)';
COMMENT ON COLUMN profiles.conference_experience IS 'Array of conferences the user has attended';
COMMENT ON COLUMN profiles.interests IS 'Array of topics the user is interested in';

-- Create a new bucket for avatar storage if it doesn't exist
INSERT INTO storage.buckets (id, name, public)
VALUES ('avatars', 'avatars', true)
ON CONFLICT (id) DO NOTHING;

-- Set up storage policies for avatars
-- Allow authenticated users to upload files to the avatars bucket
CREATE POLICY "Allow authenticated users to upload their own avatars" 
ON storage.objects FOR INSERT 
TO authenticated 
WITH CHECK (bucket_id = 'avatars' AND auth.uid()::text = SPLIT_PART(name, '-', 1));

-- Allow public access to files in the avatars bucket
CREATE POLICY "Allow public access to avatars" 
ON storage.objects FOR SELECT 
TO public 
USING (bucket_id = 'avatars');

-- Allow users to update or delete their own avatar files
CREATE POLICY "Allow users to update their own avatars" 
ON storage.objects FOR UPDATE 
TO authenticated 
USING (bucket_id = 'avatars' AND auth.uid()::text = SPLIT_PART(name, '-', 1));

CREATE POLICY "Allow users to delete their own avatars" 
ON storage.objects FOR DELETE 
TO authenticated 
USING (bucket_id = 'avatars' AND auth.uid()::text = SPLIT_PART(name, '-', 1)); 