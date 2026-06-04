# SKILL: supabase-integration

## Purpose
Manage Supabase messaging layer — auth, conversations, messages, emotion summaries.

## Scope
Supabase project (razaqxo), migration file at D:\neurotwin\supabase_migrations.sql

## Tables
- public.users (auth mirror)
- public.conversations (session-level, has emotion_summary column)
- public.conversation_messages (all messages, RLS-secured)

## Edge Function: summarize-thread
- Endpoint: POST /functions/v1/summarize-thread
- Auth: Bearer user JWT
- Input: {"conversation_id": "uuid", "max_messages": 50}
- Output: {"conversation_id", "summary", "key_points"}
- Stores result in conversations.emotion_summary

## Key Rules
- All tables are RLS-secured — always pass user JWT
- Never bypass RLS with service role key in production
- Migration script: D:\neurotwin\supabase_migrations.sql

## Pass Criteria
- summarize-thread returns 200 with summary field
- emotion_summary updated in conversations table
- RLS prevents cross-user data access

## Output Format
```json
{"supabase_connected": true, "summarize_thread_active": true, "rls_verified": true}
```
