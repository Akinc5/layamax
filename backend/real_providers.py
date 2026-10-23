"""
Production AI Providers for LayaPulse.

Implements real cloud providers (OpenAI, Gemini) for LLM synthesis and embeddings
using high-performance httpx async streaming with zero heavy dependencies.
"""
from __future__ import annotations

import json
import logging
from typing import Any, AsyncIterator, Dict, List, Optional

import httpx
import numpy as np

from config import settings
from providers import EmbeddingProvider, LLMProvider

logger = logging.getLogger("layapulse.real_providers")


# ═══════════════════════════════════════════════════════════════════════════
#  OPENAI LLM PROVIDER
# ═══════════════════════════════════════════════════════════════════════════
class OpenAILLMProvider(LLMProvider):
    """Real LLM synthesis using OpenAI GPT-4o-mini / GPT-4o with streaming."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini") -> None:
        self.api_key = api_key or settings.openai_api_key
        self.model = model

    @property
    def model_name(self) -> str:
        return self.model

    async def generate(
        self,
        prompt: str,
        context: str = "",
        system_prompt: str = "",
        max_tokens: int = 1024,
    ) -> str:
        chunks = []
        async for chunk in self.generate_stream(prompt, context, system_prompt, max_tokens):
            chunks.append(chunk)
        return "".join(chunks)

    async def generate_stream(
        self,
        prompt: str,
        context: str = "",
        system_prompt: str = "",
        max_tokens: int = 1024,
    ) -> AsyncIterator[str]:
        if not self.api_key:
            yield "Error: OPENAI_API_KEY is not set in backend/.env"
            return

        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key.strip()}",
            "Content-Type": "application/json",
        }

        user_content = f"{prompt}\n\nContext:\n{context}" if context else prompt
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_content})

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.3,
            "stream": True,
        }

        async with httpx.AsyncClient(timeout=45.0) as client:
            async with client.stream("POST", url, headers=headers, json=payload) as response:
                if response.status_code != 200:
                    err = await response.aread()
                    yield f"OpenAI API Error ({response.status_code}): {err.decode(errors='ignore')}"
                    return

                async for line in response.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    data_str = line[6:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        delta = data["choices"][0]["delta"].get("content", "")
                        if delta:
                            yield delta
                    except Exception:
                        continue


# ═══════════════════════════════════════════════════════════════════════════
#  GEMINI LLM PROVIDER
# ═══════════════════════════════════════════════════════════════════════════
class GeminiLLMProvider(LLMProvider):
    """Real LLM synthesis using Google Gemini 1.5 Flash / Pro with streaming."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-1.5-flash") -> None:
        self.api_key = api_key or settings.gemini_api_key
        self.model = model

    @property
    def model_name(self) -> str:
        return self.model

    async def generate(
        self,
        prompt: str,
        context: str = "",
        system_prompt: str = "",
        max_tokens: int = 1024,
    ) -> str:
        chunks = []
        async for chunk in self.generate_stream(prompt, context, system_prompt, max_tokens):
            chunks.append(chunk)
        return "".join(chunks)

    async def generate_stream(
        self,
        prompt: str,
        context: str = "",
        system_prompt: str = "",
        max_tokens: int = 1024,
    ) -> AsyncIterator[str]:
        if not self.api_key:
            yield "Error: GEMINI_API_KEY is not set in backend/.env"
            return

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:streamGenerateContent?key={self.api_key.strip()}"
        headers = {"Content-Type": "application/json"}

        user_content = f"{prompt}\n\nContext:\n{context}" if context else prompt
        payload: Dict[str, Any] = {
            "contents": [{"parts": [{"text": user_content}]}],
            "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.2},
        }
        if system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}

        async with httpx.AsyncClient(timeout=45.0) as client:
            async with client.stream("POST", url, headers=headers, json=payload) as response:
                if response.status_code != 200:
                    err = await response.aread()
                    yield f"Gemini API Error ({response.status_code}): {err.decode(errors='ignore')}"
                    return

                async for line in response.aiter_lines():
                    if not line or not line.strip():
                        continue
                    try:
                        clean_line = line.strip()
                        if clean_line.startswith(","):
                            clean_line = clean_line[1:].strip()
                        if clean_line.startswith("[") or clean_line.endswith("]"):
                            clean_line = clean_line.strip("[]")
                        if not clean_line:
                            continue
                        data = json.loads(clean_line)
                        candidates = data.get("candidates", [])
                        if candidates:
                            text_part = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                            if text_part:
                                yield text_part
                    except Exception:
                        continue


# ═══════════════════════════════════════════════════════════════════════════
#  OPENAI EMBEDDING PROVIDER
# ═══════════════════════════════════════════════════════════════════════════
class OpenAIEmbeddingProvider(EmbeddingProvider):
    """Production embeddings via OpenAI text-embedding-3-small."""

    def __init__(self, api_key: Optional[str] = None, model: str = "text-embedding-3-small") -> None:
        self.api_key = api_key or settings.openai_api_key
        self.model = model
        self._dim = 1536

    @property
    def dimension(self) -> int:
        return self._dim

    @property
    def model_name(self) -> str:
        return self.model

    async def embed(self, text: str) -> np.ndarray:
        res = await self.embed_batch([text])
        return res[0]

    async def embed_batch(self, texts: List[str]) -> List[np.ndarray]:
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is required for OpenAIEmbeddingProvider")

        url = "https://api.openai.com/v1/embeddings"
        headers = {
            "Authorization": f"Bearer {self.api_key.strip()}",
            "Content-Type": "application/json",
        }
        payload = {"input": texts, "model": self.model}

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code != 200:
                raise RuntimeError(f"OpenAI embedding error {resp.status_code}: {resp.text}")
            data = resp.json()
            vectors = [np.array(item["embedding"], dtype=np.float32) for item in data["data"]]
            return vectors
