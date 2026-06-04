-- ═══════════════════════════════════════════════════════════════════════════════
-- NEUROTWIN OS × SUPABASE — Database Migration
-- ═══════════════════════════════════════════════════════════════════════════════
-- Run this SQL in Supabase SQL Editor to initialize all tables

-- ───────────────────────────────────────────────────────────────────────────────
-- 1. Users Table (Supabase Auth + Profile)
-- ───────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email VARCHAR(255) UNIQUE NOT NULL,
  username VARCHAR(100) UNIQUE,
  full_name VARCHAR(255),
  avatar_url TEXT,
  bio TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- ───────────────────────────────────────────────────────────────────────────────
-- 2. Conversations Table (Chat Sessions)
-- ───────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS conversations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  title VARCHAR(500),
  emotion_summary VARCHAR(255),
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  last_message_at TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id)
);

-- ───────────────────────────────────────────────────────────────────────────────
-- 3. Messages Table
-- ───────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS conversation_messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role VARCHAR(50) NOT NULL, -- 'user' or 'assistant'
  content TEXT NOT NULL,
  metadata_json JSONB DEFAULT '{}',
  created_at TIMESTAMP DEFAULT NOW(),
  FOREIGN KEY (conversation_id) REFERENCES conversations(id),
  FOREIGN KEY (user_id) REFERENCES users(id)
);

-- ───────────────────────────────────────────────────────────────────────────────
-- 4. Memory Table (User Memories & Context)
-- ───────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS memory (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  content TEXT NOT NULL,
  memory_type VARCHAR(100), -- 'personal', 'preference', 'history', etc.
  importance_score FLOAT DEFAULT 0.5,
  embedding_id TEXT,
  metadata_json JSONB DEFAULT '{}',
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  FOREIGN KEY (user_id) REFERENCES users(id)
);

-- ───────────────────────────────────────────────────────────────────────────────
-- 5. Emotions Table (Emotion Tracking)
-- ───────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS emotions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL,
  emotion_type VARCHAR(100), -- 'happy', 'sad', 'anxious', etc.
  intensity FLOAT, -- 0-1 scale
  detected_from VARCHAR(100), -- 'text', 'voice', 'facial', 'context'
  created_at TIMESTAMP DEFAULT NOW(),
  FOREIGN KEY (user_id) REFERENCES users(id),
  FOREIGN KEY (conversation_id) REFERENCES conversations(id)
);

-- ───────────────────────────────────────────────────────────────────────────────
-- 6. Avatar Preferences Table
-- ───────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS avatar_preferences (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
  avatar_style VARCHAR(100), -- 'anime', 'realistic', 'abstract', etc.
  personality_traits JSONB DEFAULT '{}',
  voice_preference VARCHAR(100),
  color_scheme VARCHAR(50),
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  FOREIGN KEY (user_id) REFERENCES users(id)
);

-- ───────────────────────────────────────────────────────────────────────────────
-- 7. Sessions Table (Auth Sessions)
-- ───────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  token TEXT UNIQUE,
  ip_address INET,
  user_agent TEXT,
  expires_at TIMESTAMP NOT NULL,
  created_at TIMESTAMP DEFAULT NOW(),
  FOREIGN KEY (user_id) REFERENCES users(id)
);

-- ───────────────────────────────────────────────────────────────────────────────
-- Indexes for Performance
-- ───────────────────────────────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_created_at ON conversations(created_at);
CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON conversation_messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_user_id ON conversation_messages(user_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON conversation_messages(created_at);
CREATE INDEX IF NOT EXISTS idx_memory_user_id ON memory(user_id);
CREATE INDEX IF NOT EXISTS idx_memory_type ON memory(memory_type);
CREATE INDEX IF NOT EXISTS idx_emotions_user_id ON emotions(user_id);
CREATE INDEX IF NOT EXISTS idx_emotions_conversation_id ON emotions(conversation_id);
CREATE INDEX IF NOT EXISTS idx_emotions_created_at ON emotions(created_at);
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON sessions(expires_at);

-- ───────────────────────────────────────────────────────────────────────────────
-- Timestamp Update Function
-- ───────────────────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to users table
CREATE TRIGGER trigger_users_updated_at BEFORE UPDATE ON users
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Apply trigger to conversations table
CREATE TRIGGER trigger_conversations_updated_at BEFORE UPDATE ON conversations
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Apply trigger to memory table
CREATE TRIGGER trigger_memory_updated_at BEFORE UPDATE ON memory
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Apply trigger to avatar_preferences table
CREATE TRIGGER trigger_avatar_preferences_updated_at BEFORE UPDATE ON avatar_preferences
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ═══════════════════════════════════════════════════════════════════════════════
-- MIGRATION COMPLETE
-- ═══════════════════════════════════════════════════════════════════════════════
-- Your NEUROTWIN OS database is now ready!
-- All tables, indexes, and triggers are created.
-- ═══════════════════════════════════════════════════════════════════════════════
