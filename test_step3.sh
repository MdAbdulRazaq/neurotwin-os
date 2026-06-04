#!/usr/bin/env bash
set -e

API="http://localhost:8000"

echo "=== Health check ==="
curl -s "$API/health"
echo ""
echo ""

# Register test user (ignore errors if exists)
echo "=== Register test user ==="
curl -s -X POST "$API/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email":"test_step3@neurotwin.com","password":"TestPass123","name":"Step3 Tester"}' || true
echo ""
echo ""

# Login to get token
echo "=== Login ==="
LOGIN_RESP=$(curl -s -X POST "$API/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"test_step3@neurotwin.com","password":"TestPass123"}')
echo "$LOGIN_RESP"
echo ""

# Extract token (common field names: access_token, token, id_token)
TOKEN=$(echo "$LOGIN_RESP" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)
if [ -z "$TOKEN" ]; then
  TOKEN=$(echo "$LOGIN_RESP" | grep -o '"token":"[^"]*"' | cut -d'"' -f4)
fi
if [ -z "$TOKEN" ]; then
  TOKEN=$(echo "$LOGIN_RESP" | grep -o '"id_token":"[^"]*"' | cut -d'"' -f4)
fi
if [ -z "$TOKEN" ]; then
  echo "ERROR: Could not extract token from login response"
  exit 1
fi
echo "Token extracted (length ${#TOKEN})"
echo ""

# Create session
echo "=== Create session ==="
SESS_RESP=$(curl -s -X POST "$API/v1/conversation/session" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"persona_override":"default","context":""}')
echo "$SESS_RESP"
echo ""

SESSION_ID=$(echo "$SESS_RESP" | grep -o '"session_id":"[^"]*"' | cut -d'"' -f4)
if [ -z "$SESSION_ID" ]; then
  echo "ERROR: No session_id in response"
  exit 1
fi
echo "Session ID: $SESSION_ID"
echo ""

# Send message with emotion_hint=joy
echo "=== Send message with emotion_hint=joy ==="
MSG_RESP=$(curl -s -X POST "$API/v1/conversation/$SESSION_ID/message" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"content\":\"I am feeling great today!\",\"session_id\":\"$SESSION_ID\",\"emotion_hint\":\"joy\"}")
echo "$MSG_RESP"
echo ""

# Check avatar_command expression
EXPRESSION=$(echo "$MSG_RESP" | grep -o '"expression":"[^"]*"' | head -1 | cut -d'"' -f4)
echo "Avatar expression detected: \"$EXPRESSION\""
if [ "$EXPRESSION" = "smile" ]; then
  echo "✓ Step 3 TEST PASSED: joy → smile mapping works for avatar command"
else
  echo "✗ Step 3 TEST FAILED: Expected 'smile', got '$EXPRESSION'"
fi
