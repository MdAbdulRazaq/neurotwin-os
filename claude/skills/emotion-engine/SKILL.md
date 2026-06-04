# SKILL: emotion-engine

## Purpose
Detect user emotional state, adapt response style, control avatar expression intensity, influence voice pacing.

## Scope
services/api/app/routers/convo.py (_emotion_to_avatar_command)
services/api/app/core/schemas.py (EmotionLabel)
services/api/app/core/memory.py (emotion persistence)

## Emotion Labels (canonical enum)
neutral | joy | sadness | anger | fear | surprise | disgust

## Emotion → Avatar → Voice Map
| emotion   | expression  | intensity | voice_pace | blink_rate |
|-----------|-------------|-----------|------------|------------|
| joy       | smile       | 0.85      | normal     | normal     |
| sadness   | sad         | 0.70      | slow        | slow       |
| anger     | neutral     | 0.50      | measured   | fast       |
| surprise  | surprised   | 0.90      | normal     | fast       |
| fear      | sad         | 0.60      | slow        | fast       |
| disgust   | neutral     | 0.50      | normal     | normal     |
| neutral   | neutral     | 0.50      | normal     | normal     |

## Detection Sources (priority order)
1. WebSocket audio → perception service port 8001 → emotion label
2. emotion_hint field in MessageRequest body (fallback)
3. Text sentiment analysis (future)

## Persistence Rules
- Write emotion to conversation_messages.emotion column
- Write EmotionEvent to emotion_events table with intensity
- Store emotion in Redis session context for next turn

## Adaptation Rules
- joy: add warmth, increase playfulness
- sadness: slow down, validate, reduce questions
- anger: stay calm, don't match energy, ground the conversation
- surprise: match curiosity, explore together
- neutral: standard persona

## Pass Criteria
- emotion written to DB after every message
- avatar_command.expression matches emotion map
- EmotionEvent row exists in emotion_events table
- Response style shifts with detected emotion

## Output Format
```json
{"emotion": "joy", "intensity": 0.85, "avatar_expression": "smile", "db_written": true, "neo4j_written": true}
```
