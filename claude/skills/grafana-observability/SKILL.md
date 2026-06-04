# SKILL: grafana-observability

## Purpose
Monitor NEUROTWIN OS metrics — API latency, LLM call counts, container health, error rates.

## Scope
Grafana at http://localhost:3001, Prometheus at http://localhost:9090

## Key Metrics (from Prometheus)
- api_requests_total{method, endpoint, status}
- api_request_latency_seconds{endpoint}
- llm_calls_total{model, status}
- websocket_connections_total

## Dashboards to Build
1. API Health — requests/sec, error rate, p95 latency
2. LLM Performance — call count, avg latency, model usage
3. Container Health — all 13 containers uptime
4. Emotion Trends — emotion_events by label over time

## Pass Criteria
- Grafana loads at localhost:3001
- Prometheus scrapes /metrics successfully
- At least one working dashboard with live data

## Output Format
```json
{"grafana_up": true, "prometheus_up": true, "metrics_scraped": true, "dashboards": 2}
```
