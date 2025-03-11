-- Add missing columns to profiles table
ALTER TABLE profiles 
ADD COLUMN IF NOT EXISTS country TEXT,
ADD COLUMN IF NOT EXISTS school TEXT,
ADD COLUMN IF NOT EXISTS education_level TEXT CHECK (education_level IS NULL OR education_level IN ('middle_school', 'high_school', 'university', 'other')),
ADD COLUMN IF NOT EXISTS interests TEXT[],
ADD COLUMN IF NOT EXISTS conference_experience TEXT[];

-- Make sure created_at and updated_at have default values
ALTER TABLE profiles 
ALTER COLUMN created_at SET DEFAULT NOW(),
ALTER COLUMN updated_at SET DEFAULT NOW();

-- Create indexes for improved query performance
CREATE INDEX IF NOT EXISTS profiles_username_idx ON profiles(username);
CREATE INDEX IF NOT EXISTS profiles_country_idx ON profiles(country);
CREATE INDEX IF NOT EXISTS profiles_education_level_idx ON profiles(education_level);

-- Create avatars storage bucket if it doesn't exist
INSERT INTO storage.buckets (id, name, public)
SELECT 'avatars', 'avatars', true
WHERE NOT EXISTS (SELECT 1 FROM storage.buckets WHERE name = 'avatars');

-- Set up storage policies for avatars bucket
-- Drop existing policy for uploading avatars if it exists
DROP POLICY IF EXISTS "Users can upload their own avatar" ON storage.objects;

-- Policy for uploading avatars (only authenticated users can upload their own avatar)
CREATE POLICY "Users can upload their own avatar" ON storage.objects
FOR INSERT TO authenticated
WITH CHECK (
  bucket_id = 'avatars' AND
  (SUBSTRING(name FROM '^[^/]+') = auth.uid()::text)
);

-- Drop existing policy for viewing avatars if it exists
DROP POLICY IF EXISTS "Avatars are publicly accessible" ON storage.objects;

-- Policy for viewing avatars (public access)
CREATE POLICY "Avatars are publicly accessible" ON storage.objects
FOR SELECT TO public
USING (bucket_id = 'avatars');

-- Set up RLS policies for profiles table
-- Check if RLS is enabled
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_tables 
    WHERE tablename = 'profiles' 
    AND rowsecurity = true
  ) THEN
    ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
  END IF;
END
$$;

-- Modify existing policies to ensure anyone can view any profile (required for networking features)
DROP POLICY IF EXISTS "Users can view own profile" ON profiles;
CREATE POLICY "Profiles are viewable by everyone" ON profiles
FOR SELECT USING (true);

-- Ensure other policies are correctly set
DROP POLICY IF EXISTS "Users can update their own profile" ON profiles;
CREATE POLICY "Users can update their own profile" ON profiles
FOR UPDATE TO authenticated
USING (auth.uid() = id)
WITH CHECK (auth.uid() = id);

DROP POLICY IF EXISTS "Users can insert their own profile" ON profiles;
CREATE POLICY "Users can insert their own profile" ON profiles
FOR INSERT TO authenticated
WITH CHECK (auth.uid() = id);

-- Create a trigger function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION public.handle_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create a trigger to automatically update the updated_at column
DROP TRIGGER IF EXISTS on_profile_updated ON profiles;
CREATE TRIGGER on_profile_updated
BEFORE UPDATE ON profiles
FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();

-- Create a function to handle new user signup
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.profiles (id, username, created_at, updated_at)
  VALUES (
    NEW.id,
    COALESCE(split_part(NEW.email, '@', 1), NEW.id::text),
    NOW(),
    NOW()
  )
  ON CONFLICT (id) DO NOTHING;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create a trigger to automatically create a profile when a user signs up
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
AFTER INSERT ON auth.users
FOR EACH ROW EXECUTE FUNCTION public.handle_new_user(); 