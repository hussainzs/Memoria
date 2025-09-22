import json
from typing import Any, Dict, List, Optional

import httpx
from ..core.config import settings


class LLMClient:
    """Provider-agnostic lightweight LLM chat client.

    Supports providers:
    - 'ollama' (default): local models via Ollama HTTP API
    """

    def __init__(self):
        self.provider = getattr(settings, "llm_provider", "ollama") or "ollama"
        self.model = getattr(settings, "llm_model", "llama3.2:3b-instruct") or "llama3.2:3b-instruct"
        self.ollama_host = getattr(settings, "ollama_host", "http://localhost:11434") or "http://localhost:11434"
        self._openai_client = None

    def is_available(self) -> bool:
        if self.provider == "ollama":
            try:
                r = httpx.get(f"{self.ollama_host}/api/tags", timeout=1.5)
                return r.status_code == 200
            except Exception:
                return False
        return False

    def chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 512,
        temperature: float = 0.3,
        model: Optional[str] = None,
    ) -> str:
        provider_model = model or self.model
        if self.provider == "ollama":
            return self._chat_ollama(messages, provider_model, temperature)
        last_user = next((m["content"] for m in reversed(messages) if m.get("role") == "user"), "")
        return last_user[:max_tokens]

    def _chat_ollama(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
    ) -> str:
        payload = {
            "model": model,
            "messages": messages,
            "options": {"temperature": temperature},
            "stream": False,
        }
        try:
            resp = httpx.post(
                f"{self.ollama_host}/api/chat",
                json=payload,
                timeout=60.0,
            )
            if resp.status_code == 404:
                return self._chat_ollama_generate_fallback(messages, model, temperature)
            resp.raise_for_status()
            data = resp.json()
            return (data.get("message", {}) or {}).get("content", "").strip()
        except httpx.HTTPStatusError as e:
            if e.response is not None and e.response.status_code == 404:
                return self._chat_ollama_generate_fallback(messages, model, temperature)
            raise

    def _chat_ollama_generate_fallback(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
    ) -> str:
        system_prefixes = [m["content"] for m in messages if m.get("role") == "system"]
        convo_parts = []
        if system_prefixes:
            convo_parts.append("System:\n" + "\n\n".join(system_prefixes).strip())
        for m in messages:
            role = m.get("role")
            content = (m.get("content") or "").strip()
            if not content:
                continue
            if role == "user":
                convo_parts.append(f"User:\n{content}")
            elif role == "assistant":
                convo_parts.append(f"Assistant:\n{content}")
        prompt = "\n\n".join(convo_parts) + "\n\nAssistant:"

        gen_payload = {
            "model": model,
            "prompt": prompt,
            "options": {"temperature": temperature},
            "stream": False,
        }
        resp = httpx.post(
            f"{self.ollama_host}/api/generate",
            json=gen_payload,
            timeout=60.0,
        )
        resp.raise_for_status()
        data = resp.json()
        return (data.get("response") or "").strip()


