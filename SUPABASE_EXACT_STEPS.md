# SUPABASE SQL SETUP — EXACT STEP-BY-STEP GUIDE
## 🎯 Follow These Steps Perfectly

---

## **STEP 1: You Are Already Here ✅**

You should be looking at this screen:
```
URL: https://supabase.com/dashboard/project/xywuhwdijgxlfdgfktnn/...
Page Title: "Supabase Studio — SQL Editor"
Left sidebar: Shows "SQL Editor"
Main area: Shows editor with "Hit CTRL+K to generate query"
Bottom right: Shows green "Run CTRL + ↵" button
```

**✅ Confirm you see this.**

---

## **STEP 2: Clear the Editor (If needed)**

In the **white text area** (the editor), if there's any existing text:

1. **Click inside the white text area** (where it says "Hit CTRL+K...")
2. **Press Ctrl+A** (selects all text)
3. **Press Delete** (clears everything)

Now the editor should be completely empty.

---

## **STEP 3: Copy This EXACT SQL Block**

```sql
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

CREATE TABLE IF NOT EXISTS conversation_messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role VARCHAR(50) NOT NULL,
  content TEXT NOT NULL,
  metadata_json JSONB DEFAULT '{}',
  created_at TIMESTAMP DEFAULT NOW(),
  FOREIGN KEY (conversation_id) REFERENCES conversations(id),
  FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS memory (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  content TEXT NOT NULL,
  memory_type VARCHAR(100),
  importance_score FLOAT DEFAULT 0.5,
  embedding_id TEXT,
  metadata_json JSONB DEFAULT '{}',
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS emotions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL,
  emotion_type VARCHAR(100),
  intensity FLOAT,
  detected_from VARCHAR(100),
  created_at TIMESTAMP DEFAULT NOW(),
  FOREIGN KEY (user_id) REFERENCES users(id),
  FOREIGN KEY (conversation_id) REFERENCES conversations(id)
);

CREATE TABLE IF NOT EXISTS avatar_preferences (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
  avatar_style VARCHAR(100),
  personality_traits JSONB DEFAULT '{}',
  voice_preference VARCHAR(100),
  color_scheme VARCHAR(50),
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  FOREIGN KEY (user_id) REFERENCES users(id)
);

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

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_users_updated_at BEFORE UPDATE ON users
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_conversations_updated_at BEFORE UPDATE ON conversations
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_memory_updated_at BEFORE UPDATE ON memory
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_avatar_preferences_updated_at BEFORE UPDATE ON avatar_preferences
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

**To copy this:**
1. **Click the first line** (CREATE TABLE...)
2. **Scroll to the last line** (avatar_preferences...)
3. **Hold Shift + Click** at the end of the last line
4. **Press Ctrl+C** (copies to clipboard)

---

## **STEP 4: Paste Into Supabase**

1. **Click inside the white editor area** in Supabase
2. **Press Ctrl+V** (pastes the SQL)
3. **You should see all the SQL code appear** in the editor

✅ **Confirm:** The editor now contains all the SQL code.

---

## **STEP 5: Run the SQL**

Look at the **bottom right corner** of your Supabase window.

You will see a **green button** that says:
```
Run CTRL + ↵
```

**Click this button** (or press Ctrl+Enter)

---

## **STEP 6: Wait for Completion**

The screen will show:
```
Running... ⏳
```

Then after a few seconds, you'll see:
```
Success! ✅
```

Or if there's an error, it will show:
```
Error: [details]
```

---

## **STEP 7: Verify Tables Were Created**

Once you see "Success!":

1. **Click the back button** or go to: https://supabase.com/dashboard
2. **Select your project: neurotwin-os**
3. **Click on "Table Editor"** (left sidebar, under Data)
4. **You should see these 7 tables:**
   - ✅ users
   - ✅ conversations
   - ✅ conversation_messages
   - ✅ memory
   - ✅ emotions
   - ✅ avatar_preferences
   - ✅ sessions

---

## **STEP 8: Take a Screenshot**

Once you see "Success!", take a screenshot showing:
- The green "Run" button area
- The word "Success" visible
- Reply with the screenshot

---

## **SUMMARY**

| Step | Action | Result |
|------|--------|--------|
| 1 | Open Supabase SQL Editor | You're here already ✅ |
| 2 | Clear editor if needed | Empty editor |
| 3 | Copy SQL above | Copied to clipboard |
| 4 | Paste (Ctrl+V) | SQL visible in editor |
| 5 | Click green "Run" button | Executing SQL... |
| 6 | Wait for completion | See "Success!" ✅ |
| 7 | Verify 7 tables created | Check Table Editor |
| 8 | Screenshot | Show proof |

---

**READY? Follow these steps NOW and reply when you see "Success!"** 👑
