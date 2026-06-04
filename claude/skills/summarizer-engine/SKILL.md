# SKILL: summarizer-engine

## Purpose
Condense long conversations into summaries stored in memory. Powers long-term recall.

## Scope
services/api/app/core/memory.py (_summarize method), Supabase Edge Function summarize-thread

## Supabase summarize-thread Function
- Protected by RLS + user JWT
- Reads public.conversations + public.conversation_messages
- Calls OpenAI → summary + key_points
- Stores in public.conversations.emotion_summary
- Returns: {conversation_id, summary, key_points}

## Local Summarization (in-container fallback)
Current: _summarize() = first 30 words (dev stub)
Target: replace with actual LLM call to NIM proxy

## Summarization Trigger Rules
- After every 20 messages in a session
- On session end
- When user says "remember this" or "don't forget"

## Output Format
```json
{"summary": "CEO Razaq discussed work stress and joy in creative projects.", "key_points": ["work", "creativity", "joy"], "stored": true}
```
