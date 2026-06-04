# SKILL: visual-identity-engine (VERIFIED LIVE 2026-04-05)

## Purpose
Convert emotion state into full visual parameters — color palette, eye features, mouth features, skin tone, special effects.

## Service
URL: http://localhost:8005 (container: neurotwin-visual-identity, port 8005)
Health: GET /health → {"status":"ok","service":"visual-identity"}

## VERIFIED ENDPOINTS

### POST /v1/style/emotion
Input:
{"emotion":"joy","intensity":0.85,"confidence":0.91,"text_context":"optional context"}

Output (live verified):
{"visual_state":{"emotion":"joy","intensity":0.85,
  "color_palette":{"primary":"#FFE4B5","secondary":"#FFB347","highlight":"#FFD700","shadow":"#DEB887"},
  "eye_features":{"brightness":1.24,"size_multiplier":1.44,"sharpness":1.1,"pupil_dilation":0.9,"highlight_intensity":1.275},
  "mouth_features":{"curvature":0.68,"openness":0.17,"width":1.2,"tension":0.0},
  "skin_tone":{"base_hue":"#E8BEAC","saturation":1.0,"warmth":1.26},
  "special_effects":["soft_glow","sparkle_highlights"],
  "metadata":{"roughness":0.3,"metalness":0.0,"subsurface_scatter":0.1}},
"blend_time_ms":300,"description":"Warm, bright appearance with golden tones and sparkling eyes"}

### GET /v1/style/palette/{emotion}
Input: /v1/style/palette/joy
Output: {"emotion":"joy","palette":{"primary":"#FFE4B5","secondary":"#FFB347","highlight":"#FFD700","shadow":"#DEB887"},"warmth_multiplier":1.17}

Emotion palettes verified:
- joy:     primary:#FFE4B5 (warm gold)
- sadness: primary:#B0C4DE (steel blue)

### POST /v1/style/enrich-avatar-command
Query params: ?emotion=joy
Body: {"avatar_command":{...}}
NOTE: emotion must be a QUERY PARAM not body field

## Emotion → Visual Rules (canonical)
- joy:      golden/warm tones, bright eyes, wide smile, soft_glow + sparkle
- sadness:  steel blue tones, dim eyes, slight frown, rain_shimmer
- anger:    red tones, sharp eyes, tense mouth, heat_distortion
- surprise: cyan tones, wide eyes, open mouth
- neutral:  warm white tones, balanced features

## Integration with Cognition Engine
After every LLM response, call /v1/style/emotion with the detected emotion
to get visual_state → send to AvatarCanvas.tsx alongside avatar_command

## Pass Criteria
- POST /v1/style/emotion returns visual_state with all 6 fields
- color_palette.primary changes per emotion
- eye_features.curvature matches emotion type
- AvatarCanvas renders enriched colors

## Output Format
```json
{"visual_state_applied": true, "emotion": "joy", "palette": "#FFE4B5", "special_effects": ["soft_glow"]}
```
