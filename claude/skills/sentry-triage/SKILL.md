# SKILL: sentry-triage

## Purpose
Capture, group, and debug NEUROTWIN OS errors in production.

## Scope
services/api/app/main.py (sentry_sdk integration), Sentry MCP connector

## Setup (in config.py)
SENTRY_DSN: Optional[str] = None  → set in .env to activate

## Key Error Groups to Monitor
- LLM call failures (NIM proxy down)
- DB write failures (memory store errors)
- JWT auth failures
- Neo4j connection errors
- SSE stream errors

## Triage Process
1. Check Sentry for new issues after every deployment
2. Group by fingerprint (same error, different users)
3. Assign priority: P1=system down, P2=feature broken, P3=cosmetic
4. Fix P1 immediately, P2 in current sprint, P3 backlog

## Pass Criteria
- Sentry receives at least test error after setup
- Error fingerprinting groups similar errors correctly

## Output Format
```json
{"sentry_active": true, "new_issues": 0, "p1_count": 0, "p2_count": 0}
```
