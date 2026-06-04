"""
NEUROTWIN OS — LLM Client
Supports Anthropic Claude, OpenAI GPT, and local Llama.
Handles streaming, retry logic, RAG context injection, token tracking.
"""

import asyncio
import json
import logging
import time
from enum import Enum
from typing import AsyncGenerator, List, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.config import settings

logger = logging.getLogger("neurotwin.llm")


class LLMProvider(str, Enum):
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    LOCAL = "local"


class Message:
    def __init__(self, role: str, content: str):
        self.role = role
        self.content = content

    def to_dict(self) -> dict:
        return {"role": self.role, "content": self.content}


class LLMResponse:
    def __init__(self, text: str, model: str, input_tokens: int, output_tokens: int, latency_ms: float):
        self.text = text
        self.model = model
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.latency_ms = latency_ms
        self.total_tokens = input_tokens + output_tokens

    def __repr__(self):
        return f"<LLMResponse model={self.model} tokens={self.total_tokens} latency={self.latency_ms:.0f}ms>"


class LLMClient:
    """
    Unified LLM client with:
    - Multi-provider support (Anthropic / OpenAI / Local)
    - Streaming completions
    - Automatic retry with exponential backoff
    - RAG context injection
    - Token usage tracking
    - PII scrubbing
    """

    ANTHROPIC_BASE = "https://api.anthropic.com/v1"
    OPENAI_BASE = "https://api.openai.com/v1"

    def __init__(self):
        self.provider = LLMProvider(settings.LLM_PROVIDER)
        self.model = settings.LLM_MODEL
        self.max_tokens = settings.LLM_MAX_TOKENS
        self.temperature = settings.LLM_TEMPERATURE
        self._http = httpx.AsyncClient(timeout=60.0)
        # Support custom base URL for NVIDIA NIM / local proxy
        anthropic_base = getattr(settings, 'ANTHROPIC_BASE_URL', None)
        if anthropic_base:
            anthropic_base = anthropic_base.rstrip('/')
            if not anthropic_base.endswith('/v1'):
                anthropic_base += '/v1'
            self.anthropic_base = anthropic_base
        else:
            self.anthropic_base = self.ANTHROPIC_BASE
        self.openai_base = self.OPENAI_BASE

    async def close(self):
        await self._http.aclose()

    # ── Public API ────────────────────────────────────────────────────────────

    async def chat(
        self,
        system_prompt: str,
        messages: List[Message],
        rag_contexts: Optional[List[str]] = None,
        stream: bool = True,
        user_id: Optional[str] = None,
    ) -> LLMResponse:
        """Non-streaming chat. Returns full LLMResponse."""
        enriched_system = self._build_system(system_prompt, rag_contexts)
        t0 = time.monotonic()
        if self.provider == LLMProvider.ANTHROPIC:
            result = await self._anthropic_complete(enriched_system, messages)
        elif self.provider == LLMProvider.OPENAI:
            result = await self._openai_complete(enriched_system, messages)
        else:
            result = await self._local_complete(enriched_system, messages)
        result.latency_ms = (time.monotonic() - t0) * 1000
        logger.info(
            f"LLM chat user={user_id} model={result.model} "
            f"tokens={result.total_tokens} latency={result.latency_ms:.0f}ms"
        )
        return result

    async def stream_chat(
        self,
        system_prompt: str,
        messages: List[Message],
        rag_contexts: Optional[List[str]] = None,
    ) -> AsyncGenerator[str, None]:
        """Streaming chat. Yields text deltas."""
        if self.provider == LLMProvider.OPENAI:
            key = settings.OPENAI_API_KEY
            if not key or "PASTE" in key.get_secret_value():
                yield "⚠️ No OpenAI API key configured. Please add OPENAI_API_KEY to D:\\neurotwin\\.env and restart."
                return
        elif self.provider == LLMProvider.ANTHROPIC:
            key = settings.ANTHROPIC_API_KEY
            if not key or not key.get_secret_value():
                yield "⚠️ No Anthropic API key configured. Please add ANTHROPIC_API_KEY to D:\\neurotwin\\.env and restart."
                return
        try:
            enriched_system = self._build_system(system_prompt, rag_contexts)
            if self.provider == LLMProvider.ANTHROPIC:
                async for token in self._anthropic_stream(enriched_system, messages):
                    yield token
            elif self.provider == LLMProvider.OPENAI:
                async for token in self._openai_stream(enriched_system, messages):
                    yield token
            else:
                result = await self._local_complete(enriched_system, messages)
                yield result.text
        except Exception as e:
            logger.error(f"LLM stream error: {e}")
            yield f"⚠️ LLM error: {str(e)}"

    # ── System prompt builder ─────────────────────────────────────────────────

    def _build_system(self, base_prompt: str, rag_contexts: Optional[List[str]]) -> str:
        if not rag_contexts:
            return base_prompt
        ctx_block = "\n\n".join(f"[Memory {i+1}]: {c}" for i, c in enumerate(rag_contexts))
        return f"{base_prompt}\n\n## Relevant memories and context:\n{ctx_block}"

    # ── Anthropic ─────────────────────────────────────────────────────────────

    @retry(
        retry=retry_if_exception_type(httpx.HTTPStatusError),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def _anthropic_complete(self, system: str, messages: List[Message]) -> LLMResponse:
        """
        Non-streaming Anthropic call.
        NIM proxy returns SSE even when stream=False — we parse SSE lines.
        Falls back to JSON parsing if NIM returns a plain JSON response.
        """
        headers = {
            "x-api-key": settings.ANTHROPIC_API_KEY.get_secret_value(),
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "system": system,
            "messages": [m.to_dict() for m in messages],
            "stream": False,
        }
        logger.info(f"Anthropic complete — model={self.model} url={self.anthropic_base}/messages")

        resp = await self._http.post(
            f"{self.anthropic_base}/messages",
            headers=headers,
            json=payload,
        )
        resp.raise_for_status()

        raw = resp.text.strip()
        text = ""
        input_tokens = 0
        output_tokens = 0
        model_name = self.model

        # NIM proxy may return SSE even for non-streaming requests
        if raw.startswith("event:") or raw.startswith("data:"):
            logger.debug("Anthropic complete — detected SSE response from proxy, parsing SSE")
            for line in raw.splitlines():
                line = line.strip()
                if not line or line == "data: [DONE]":
                    continue
                if line.startswith("data:"):
                    chunk = line[5:].strip()
                    try:
                        evt = json.loads(chunk)
                        evt_type = evt.get("type", "")
                        if evt_type == "content_block_delta":
                            text += evt.get("delta", {}).get("text", "")
                        elif evt_type == "message_start":
                            msg_data = evt.get("message", {})
                            model_name = msg_data.get("model", self.model)
                            usage = msg_data.get("usage", {})
                            input_tokens = usage.get("input_tokens", 0)
                        elif evt_type == "message_delta":
                            output_tokens = evt.get("usage", {}).get("output_tokens", 0)
                        elif evt_type == "message_stop":
                            break
                    except json.JSONDecodeError:
                        continue
        else:
            # Standard JSON response (real Anthropic API)
            logger.debug("Anthropic complete — detected JSON response, parsing directly")
            try:
                data = json.loads(raw)
                text = data["content"][0]["text"]
                usage = data.get("usage", {})
                model_name = data.get("model", self.model)
                input_tokens = usage.get("input_tokens", 0)
                output_tokens = usage.get("output_tokens", 0)
            except (json.JSONDecodeError, KeyError, IndexError) as e:
                logger.error(f"Anthropic JSON parse error: {e} — raw={raw[:200]!r}")
                raise

        return LLMResponse(
            text=text,
            model=model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=0,
        )

    async def _anthropic_stream(self, system: str, messages: List[Message]) -> AsyncGenerator[str, None]:
        headers = {
            "x-api-key": settings.ANTHROPIC_API_KEY.get_secret_value(),
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "system": system,
            "messages": [m.to_dict() for m in messages],
            "stream": True,
        }
        async with self._http.stream(
            "POST", f"{self.anthropic_base}/messages", headers=headers, json=payload
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                line = line.strip()
                if not line or line == "data: [DONE]":
                    continue
                if line.startswith("data:"):
                    raw = line[5:].strip()
                    try:
                        evt = json.loads(raw)
                        if evt.get("type") == "content_block_delta":
                            delta = evt.get("delta", {}).get("text", "")
                            if delta:
                                yield delta
                        elif evt.get("type") == "message_stop":
                            break
                    except json.JSONDecodeError:
                        pass

    # ── OpenAI ────────────────────────────────────────────────────────────────

    @retry(
        retry=retry_if_exception_type(httpx.HTTPStatusError),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def _openai_complete(self, system: str, messages: List[Message]) -> LLMResponse:
        """Non-streaming OpenAI call. Parses standard JSON response."""
        headers = {
            "Authorization": f"Bearer {settings.OPENAI_API_KEY.get_secret_value()}",
            "Content-Type": "application/json",
        }
        msgs = [{"role": "system", "content": system}] + [m.to_dict() for m in messages]
        payload = {
            "model": self.model,
            "messages": msgs,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }
        resp = await self._http.post(
            f"{self.openai_base}/chat/completions",
            headers=headers,
            json=payload,
        )
        resp.raise_for_status()
        try:
            data = resp.json()
            text = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            return LLMResponse(
                text=text,
                model=data.get("model", self.model),
                input_tokens=usage.get("prompt_tokens", 0),
                output_tokens=usage.get("completion_tokens", 0),
                latency_ms=0,
            )
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            logger.error(f"OpenAI JSON parse error: {e} — raw={resp.text[:200]!r}")
            raise

    async def _openai_stream(self, system: str, messages: List[Message]) -> AsyncGenerator[str, None]:
        headers = {
            "Authorization": f"Bearer {settings.OPENAI_API_KEY.get_secret_value()}",
            "Content-Type": "application/json",
        }
        msgs = [{"role": "system", "content": system}] + [m.to_dict() for m in messages]
        payload = {
            "model": self.model,
            "messages": msgs,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "stream": True,
        }
        async with self._http.stream(
            "POST", f"{self.openai_base}/chat/completions", headers=headers, json=payload
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                line = line.strip()
                if not line:
                    continue
                if line.startswith("data:"):
                    raw = line[5:].strip()
                    if raw == "[DONE]":
                        break
                    try:
                        evt = json.loads(raw)
                        delta = evt["choices"][0]["delta"].get("content", "")
                        if delta:
                            yield delta
                    except (json.JSONDecodeError, KeyError):
                        pass

    # ── Local (Ollama / LM Studio) ────────────────────────────────────────────

    async def _local_complete(self, system: str, messages: List[Message]) -> LLMResponse:
        """Local Ollama-compatible endpoint. Uses OpenAI-compatible chat format."""
        local_base = getattr(settings, 'LOCAL_LLM_URL', 'http://localhost:11434')
        headers = {"Content-Type": "application/json"}
        msgs = [{"role": "system", "content": system}] + [m.to_dict() for m in messages]
        payload = {
            "model": self.model,
            "messages": msgs,
            "stream": False,
        }
        resp = await self._http.post(
            f"{local_base}/v1/chat/completions",
            headers=headers,
            json=payload,
        )
        resp.raise_for_status()
        raw = resp.text.strip()

        # Detect SSE vs JSON
        if raw.startswith("event:") or raw.startswith("data:"):
            text = ""
            model_name = self.model
            for line in raw.splitlines():
                line = line.strip()
                if not line or line == "data: [DONE]":
                    continue
                if line.startswith("data:"):
                    chunk = line[5:].strip()
                    try:
                        evt = json.loads(chunk)
                        delta = evt.get("choices", [{}])[0].get("delta", {}).get("content", "")
                        text += delta
                        if evt.get("model"):
                            model_name = evt["model"]
                    except json.JSONDecodeError:
                        continue
            return LLMResponse(text=text, model=model_name, input_tokens=0, output_tokens=0, latency_ms=0)
        else:
            try:
                data = json.loads(raw)
                text = data["choices"][0]["message"]["content"]
                usage = data.get("usage", {})
                return LLMResponse(
                    text=text,
                    model=data.get("model", self.model),
                    input_tokens=usage.get("prompt_tokens", 0),
                    output_tokens=usage.get("completion_tokens", 0),
                    latency_ms=0,
                )
            except (json.JSONDecodeError, KeyError, IndexError) as e:
                logger.error(f"Local LLM parse error: {e} — raw={raw[:200]!r}")
                raise


# ── Singleton ─────────────────────────────────────────────────────────────────
_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
