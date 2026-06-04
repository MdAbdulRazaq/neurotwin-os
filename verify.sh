#!/usr/bin/env bash
# verify.sh — NEUROTWIN OS health check
# Run from D:\neurotwin: bash verify.sh
PASS=0; FAIL=0

check_container() {
  local svc=$1
  local status
  status=$(docker inspect --format='{{.State.Status}}' "$svc" 2>/dev/null || echo "missing")
  if [[ "$status" == "running" ]]; then
    echo "  [OK]   $svc → $status"
    PASS=$((PASS + 1))
  else
    echo "  [FAIL] $svc → $status"
    FAIL=$((FAIL + 1))
  fi
}

check_endpoint() {
  local name=$1; local url=$2
  if curl -sf "$url" -o /dev/null 2>/dev/null; then
    echo "  [OK]   $name"
    PASS=$((PASS + 1))
  else
    echo "  [FAIL] $name"
    FAIL=$((FAIL + 1))
  fi
}

echo "=== Container status ==="
check_container "neurotwin-postgres"
check_container "neurotwin-redis"
check_container "neurotwin-orchestrator"
check_container "neurotwin-prediction"
check_container "neurotwin-voice"

echo ""
echo "=== Health endpoints ==="
check_endpoint "prediction  :8009 /health" "http://localhost:8009/health"
check_endpoint "orchestrator :8010 /health" "http://localhost:8010/health"
check_endpoint "voice        :8011 /health" "http://localhost:8011/health"

echo ""
echo "=== Redis active channels ==="
echo "  $(docker exec neurotwin-redis redis-cli PUBSUB CHANNELS 'neurotwin:*' 2>/dev/null | tr '\n' ' ')"

echo ""
echo "=== Learning pattern store ==="
count=$(docker exec neurotwin-redis redis-cli HLEN neurotwin:patterns 2>/dev/null || echo "0")
echo "  neurotwin:patterns → ${count} keys"

echo ""
if [[ $FAIL -eq 0 ]]; then
  echo "=== RESULT: $PASS passed, 0 failed — ALL SYSTEMS HEALTHY ==="
else
  echo "=== RESULT: $PASS passed, $FAIL failed — ACTION REQUIRED ==="
fi
