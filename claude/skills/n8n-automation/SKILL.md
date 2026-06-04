# SKILL: n8n-automation

## Purpose
Automate NEUROTWIN workflows — session triggers, notification hooks, data pipeline automation.

## Scope
n8n instance at razaqxo.app.n8n.cloud

## Key Automation Workflows to Build
1. New session created → log to Notion
2. Emotion spike detected (anger/sadness) → send alert
3. Daily summary → pull analytics and post to Notion
4. Memory threshold hit → trigger summarizer-engine
5. Docker container down → send notification

## Webhook Pattern
POST to n8n webhook URL with payload:
{"event": "emotion_spike", "user_id": "...", "emotion": "sadness", "session_id": "..."}

## Pass Criteria
- n8n workflow receives NEUROTWIN webhook events
- Automation triggers correctly on emotion events
- Daily digest workflow runs on schedule

## Output Format
```json
{"workflow_triggered": true, "workflow_name": "emotion-alert", "status": "success"}
```
