-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create chats table
CREATE TABLE IF NOT EXISTS chats (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id TEXT NOT NULL,
  title TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create messages table with reference to chats
CREATE TABLE IF NOT EXISTS messages (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  chat_id UUID REFERENCES chats(id) ON DELETE CASCADE,
  role TEXT NOT NULL,  -- 'user', 'system', 'editor', 'upload', 'error'
  content TEXT NOT NULL,  -- JSON stringified content including documentId, documentType, etc.
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  order_index INTEGER NOT NULL
);

-- Create index for faster message retrieval
CREATE INDEX IF NOT EXISTS messages_chat_id_idx ON messages (chat_id);

-- Create index for faster chat listing by user
CREATE INDEX IF NOT EXISTS chats_user_id_idx ON chats (user_id);

-- Add RLS (Row Level Security) policies for chat tables
ALTER TABLE chats ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;

-- Create a policy to allow users to access only their own chats
CREATE POLICY chat_user_access ON chats
  FOR ALL
  USING (user_id = auth.uid());

-- Create a policy that restricts message access based on chat access
CREATE POLICY message_chat_access ON messages
  FOR ALL
  USING (
    chat_id IN (
      SELECT id FROM chats WHERE user_id = auth.uid()
    )
  ); 