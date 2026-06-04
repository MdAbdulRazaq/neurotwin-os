# SKILL: avatar-engine

## Purpose
Convert LLM emotional output into avatar blendshape commands. Control facial sync, idle, lip movement.

## Scope
web/components/avatar/AvatarCanvas.tsx, services/api/app/routers/convo.py (_emotion_to_avatar_command)

## Avatar Command Schema (canonical — never deviate)
```json
{
  "type": "expression",
  "expression": "smile|sad|surprised|thinking|neutral|excited",
  "intensity": 0.0-1.0,
  "duration_ms": 3000,
  "blend": true,
  "eye_focus": "user|away|down",
  "blink_rate": "normal|fast|slow",
  "head_tilt": -0.3 to 0.3
}
```

## SSE Avatar Frames (streaming integration)
- Frame 1 of every stream: {"type":"avatar","data":"thinking"} → shows thinking state
- Final done frame: {"type":"done","metadata":{"avatar_command":{...}}} → final expression

## Idle Behavior Rules (must always run)
- Blink every 2-6 seconds (randomized)
- Eye drift: ±5px natural movement every 3s
- Breathing: subtle scale animation 4s cycle
- Head micro-movement: ±2deg every 8s

## Transition Rules
- Never instant expression change — always ease-in 300ms
- Blend=true means cross-fade from current expression
- thinking expression triggered when text ends with "?"

## Allowed Files
- web/components/avatar/AvatarCanvas.tsx
- services/api/app/routers/convo.py

## Pass Criteria
- Every /message response contains avatar_command
- Every /stream done frame contains avatar_command
- AvatarCanvas renders without console errors
- Idle animations run even when not speaking

## Output Format
```json
{"avatar_command_sent": true, "expression": "smile", "idle_active": true, "blend": true}
```
