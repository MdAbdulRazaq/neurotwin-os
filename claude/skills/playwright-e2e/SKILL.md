# SKILL: playwright-e2e

## Purpose
Browser-level automated testing of NEUROTWIN OS frontend.

## Scope
web/ Next.js app at http://localhost, Playwright MCP connector

## Test Scenarios
1. Login flow: navigate to /auth/login → fill email/password → submit → redirect to /chat
2. Chat flow: send message → verify response appears in chat UI → verify avatar reacts
3. Dashboard: navigate to /dashboard → verify metric cards show non-zero values
4. Health route: GET http://localhost/health → verify {"status":"healthy"}
5. SSE: open /chat → send message → verify streaming tokens appear progressively

## Browser Setup
- Base URL: http://localhost
- Test user: ceo2@neurotwin.ai / NeuroCEO2026!
- Headless mode for CI, headed for debugging

## Pass Criteria
- Login redirects to /chat within 3s
- Chat response visible within 10s
- Dashboard shows total_messages > 0
- No console errors during any flow

## Output Format
```json
{"login": true, "chat": true, "dashboard": true, "health": true, "sse": true, "errors": 0}
```
