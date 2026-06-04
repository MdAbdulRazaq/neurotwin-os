# SKILL: image-generation

## Purpose
Generate anime-realistic character visuals for NEUROTWIN avatar using Nano Banana MCP.

## Scope
Nano Banana MCP (AI image generation), web/public/avatar/ (output directory)

## Base Character Prompt (canonical)
"realistic anime female companion, soft cinematic lighting, expressive dark eyes,
natural skin tone, subtle imperfections, warm gentle smile, high detail portrait,
4K, professional photography style, no harsh filters"

## Emotion Variant Prompts
- joy: append "bright joyful smile, eyes slightly curved, warm lighting"
- sadness: append "gentle downward gaze, soft expression, muted tones"
- surprise: append "wide eyes, slightly open mouth, raised eyebrows"
- thinking: append "slight head tilt, focused gaze, finger near chin"
- neutral: append "calm serene expression, direct eye contact"

## Generation Rules
- Always use same character seed for consistency
- Resolution: minimum 512x512, prefer 1024x1024
- Style: anime-realistic NOT full cartoon, NOT hyperrealistic photo
- NEVER generate NSFW, violent, or inappropriate content

## Output Directory
D:\neurotwin\web\public\avatar\
Naming: emotion_joy.png, emotion_sad.png, emotion_neutral.png, etc.

## Pass Criteria
- Character looks consistent across all emotion variants
- Expressions clearly readable at small sizes (128x128)
- Style maintains anime-realistic quality (not cartoon)

## Output Format
```json
{"images_generated": 6, "style": "anime-realistic", "consistent_identity": true}
```
