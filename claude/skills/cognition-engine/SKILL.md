# SKILL: cognition-engine

## Purpose
LLM reasoning brain — process input, inject memory, generate response via NIM proxy.

## Scope
services/api/app/core/llm_client.py, services/api/app/routers/convo.py

## Allowed Files
- services/api/app/core/llm_client.py
- services/api/app/routers/convo.py
- services/api/app/core/config.py

## LLM Pipeline
1. Build system prompt: NEUROTWIN_PERSONA.format(user_name, preferences, emotion)
2. Inject RAG contexts: memory_manager.get_context_for_prompt()
3. Call llm.chat() or llm.stream_chat()
4. Return LLMResponse(text, model, tokens, latency)

## NIM Proxy Config
- URL: http://host.docker.internal:8082/v1
- Model: meta/llama-3.1-8b-instruct
- API Key: freecc
- Max tokens: 1024, Temperature: 0.7

## SSE Stream Format (verified)
- Frame 1: {"type":"avatar","data":"thinking"}
- Frames 2-N: {"type":"token","data":"<word>"}
- Final: {"type":"done","metadata":{"avatar_command":{...}}}

## Pass Criteria
- /message returns 200 with content field
- /stream returns 200, content-type: text/event-stream
- At least 5 token frames received
- latency_ms < 10000

## Failure Rules
- If "All connection attempts failed" → NIM proxy is down, restart it
- If IndentationError → stale .pyc, rebuild container
- Never call resp.json() on SSE response — always parse data: lines

## Output Format
```json
{"response": "...", "latency_ms": 1800, "tokens": 48, "model": "meta/llama-3.1-8b-instruct"}
```
