# SKILL: perception-engine

## Purpose
Voice → transcript → emotion → structured perception result for Cognition Engine.

## Scope
services/api/app/routers/ perception routes, port 8001 service, useVoice.ts WebSocket hook

## Allowed Files
- services/api/app/routers/convo.py (emotion_hint injection)
- web/lib/hooks/useVoice.ts
- services/perception/

## Allowed Tools
Desktop Commander, docker exec, Invoke-WebRequest

## Exact Tasks
1. Verify perception service: `GET http://localhost:8001/health`
2. Send audio/emotion signal via WebSocket to port 8001
3. Confirm emotion_hint flows into POST /v1/conversation/{sid}/message body
4. Verify emotion label appears in conversation_messages.emotion column
5. Confirm avatar_command reflects detected emotion (joy→smile, sad→sad, etc.)

## Emotion → Avatar Map (canonical)
- joy → smile (intensity 0.85)
- sadness → sad (intensity 0.7)
- anger → neutral (intensity 0.5)
- surprise → surprised (intensity 0.9)
- fear → sad (intensity 0.6)
- neutral → neutral (intensity 0.5)

## Pass Criteria
- perception health = ok
- emotion_hint accepted in message body
- avatar_command.expression matches emotion map
- emotion written to DB

## Failure Rule
Do not modify cognition engine if perception pipe is broken.

## Output Format
```json
{"emotion": "joy", "intensity": 0.85, "confidence": 0.91, "avatar_command": {"expression": "smile"}}
```
