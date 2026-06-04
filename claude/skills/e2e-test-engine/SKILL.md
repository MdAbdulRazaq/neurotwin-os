# SKILL: codereview-engine (VERIFIED LIVE 2026-04-05)

## Purpose
Structural code analysis using AST graph. Tracks co-change patterns, quality scores, architectural hotspots.
8.2x token reduction for Claude Code sessions.

## Service
URL: http://localhost:8004 (container: neurotwin-codereview, port 8004)
Health: GET /health → {"status":"ok","service":"codereview","neo4j_connected":true,"repo_loaded":false}

## VERIFIED ENDPOINTS

### POST /v1/analyze
Body: {"path": "D:/neurotwin"}
Builds AST graph of codebase. Initial build ~10s for 500 files.

### GET /v1/files/{file_path}/cochange
Returns files that frequently change together with the given file.

### GET /v1/files/{file_path}/quality
Returns quality score for a specific file.

### GET /v1/report/architectural-hotspots
Returns files with highest complexity + churn.

### GET /v1/report/churn
Returns files changed most frequently.

### GET /v1/report/quality
Returns quality scores across entire codebase.

### GET /v1/graph/stats (VERIFIED)
Returns: {"graph_statistics":{"User":2,"Session":11,"Message":42,"EmotionPattern":2,...}}

### GET /v1/graph/coupling-path
Returns coupling path between two files.

## Install for Claude Code Sessions
pip install code-review-graph
cd D:\neurotwin
code-review-graph install --platform claude-code
code-review-graph build
# Gives Claude Code structural awareness — reads only what matters

## Pass Criteria
- /health returns neo4j_connected: true
- /v1/analyze builds graph without errors
- /v1/graph/stats returns non-zero counts
- Claude Code sessions use graph for context

## Output Format
```json
{"graph_built": true, "files_analyzed": 120, "hotspots": 3, "quality_score": 0.78}
```
