@echo off
:: NEUROTWIN OS - Claude Code via NVIDIA NIM Proxy (Primary, always works)
:: Uses the existing free-claude-code proxy at localhost:8082
:: Start proxy first: cd D:\free-claude-code && uv run uvicorn server:app --host 0.0.0.0 --port 8082

title Claude Code [NIM Proxy - FREE]
cd /d D:\neurotwin

set ANTHROPIC_AUTH_TOKEN=freecc
set ANTHROPIC_BASE_URL=http://localhost:8082/v1
set CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1

echo.
echo ========================================
echo  NEUROTWIN OS - Claude Code
echo  Mode: NVIDIA NIM Proxy (localhost:8082)
echo  Project: D:\neurotwin
echo ========================================
echo.

claude
