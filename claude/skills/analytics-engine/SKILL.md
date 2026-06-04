# SKILL: analytics-engine

## Purpose
Surface real user data on the dashboard. Wire /v1/analytics/summary to live PostgreSQL data.

## Scope
services/api/app/routers/analytics.py, web/app/dashboard/page.tsx

## API Endpoint
GET /v1/analytics/summary?period_days=7
Returns: total_sessions, total_messages, avg_session_length_minutes, top_topics, mood_timeline, engagement_score

## Dashboard Wiring Check
1. Confirm analyticsApi.summary(period) calls /v1/analytics/summary
2. Confirm dashboard page renders returned data (not placeholders)
3. After sending 3+ messages, reload dashboard and verify counts increase

## Pass Criteria
- total_messages > 0 after real conversation
- mood_timeline has emotion data points
- engagement_score > 0
- Dashboard at http://localhost/dashboard shows real numbers

## Output Format
```json
{"total_sessions": 2, "total_messages": 4, "engagement_score": 0.13, "dashboard_live": true}
```
