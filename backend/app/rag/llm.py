import json
import logging
import re
import time
from abc import ABC, abstractmethod
from functools import lru_cache

import httpx

from app.config import get_settings

logger = logging.getLogger("studysphere.llm")


class LLMError(Exception):
    """Raised when the model provider is unconfigured or unavailable. Detail goes to logs, not users."""


class LLMProvider(ABC):
    @abstractmethod
    def generate(self, system: str, user: str) -> str:
        """Return the model's raw text reply (expected to be a JSON object)."""


def _post(url: str, *, headers: dict, body: dict, timeout: float = 60) -> dict:
    last = None
    for attempt in range(2):  # one retry on rate-limit / transient server errors
        try:
            r = httpx.post(url, headers=headers, json=body, timeout=timeout)
        except httpx.HTTPError as exc:
            last = exc
        else:
            if r.status_code < 400:
                return r.json()
            last = LLMError(f"HTTP {r.status_code}: {r.text[:300]}")
            if r.status_code not in (429, 500, 502, 503, 504):
                break
        time.sleep(1.5)
    raise LLMError(f"Provider request failed: {last}")


class GeminiProvider(LLMProvider):
    def __init__(self, key: str, model: str):
        if not key:
            raise LLMError("GEMINI_API_KEY is not set.")
        self.key, self.model = key, model

    def generate(self, system: str, user: str) -> str:
        data = _post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent",
            headers={"x-goog-api-key": self.key},  # key travels in a header, never in the URL/logs
            body={
                "systemInstruction": {"parts": [{"text": system}]},
                "contents": [{"role": "user", "parts": [{"text": user}]}],
                "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"},
            },
        )
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError(f"Unexpected Gemini response: {str(data)[:300]}") from exc


class OpenAICompatProvider(LLMProvider):
    def __init__(self, key: str, base_url: str, model: str):
        if not key:
            raise LLMError("OPENAI_API_KEY is not set.")
        self.key, self.base, self.model = key, base_url.rstrip("/"), model

    def generate(self, system: str, user: str) -> str:
        data = _post(
            f"{self.base}/chat/completions",
            headers={"Authorization": f"Bearer {self.key}"},
            body={"model": self.model, "temperature": 0.2, "response_format": {"type": "json_object"},
                  "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]},
        )
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError("Unexpected OpenAI-compatible response.") from exc


class AnthropicProvider(LLMProvider):
    def __init__(self, key: str, model: str):
        if not key:
            raise LLMError("ANTHROPIC_API_KEY is not set.")
        self.key, self.model = key, model

    def generate(self, system: str, user: str) -> str:
        data = _post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": self.key, "anthropic-version": "2023-06-01"},
            body={"model": self.model, "max_tokens": 1500, "temperature": 0.2, "system": system,
                  "messages": [{"role": "user", "content": user}]},
        )
        try:
            return "".join(b.get("text", "") for b in data["content"] if b.get("type") == "text")
        except (KeyError, TypeError) as exc:
            raise LLMError("Unexpected Anthropic response.") from exc


class OllamaProvider(LLMProvider):
    def __init__(self, base_url: str, model: str):
        self.base, self.model = base_url.rstrip("/"), model

    def generate(self, system: str, user: str) -> str:
        data = _post(
            f"{self.base}/api/chat", headers={}, timeout=180,
            body={"model": self.model, "stream": False, "format": "json", "options": {"temperature": 0.2},
                  "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]},
        )
        try:
            return data["message"]["content"]
        except (KeyError, TypeError) as exc:
            raise LLMError("Unexpected Ollama response.") from exc


_DEFAULT_MODELS = {"openai": "gpt-4o-mini", "anthropic": "claude-haiku-4-5-20251001", "ollama": "llama3.1"}


@lru_cache
def get_llm() -> LLMProvider:
    s = get_settings()
    p = s.llm_provider.lower()
    if p == "gemini":
        return GeminiProvider(s.gemini_api_key, s.llm_model or s.gemini_model)
    model = s.llm_model or _DEFAULT_MODELS.get(p, "")
    if p == "openai":
        return OpenAICompatProvider(s.openai_api_key, s.openai_base_url, model)
    if p == "anthropic":
        return AnthropicProvider(s.anthropic_api_key, model)
    if p == "ollama":
        return OllamaProvider(s.ollama_base_url, model)
    raise LLMError(f"Unknown LLM_PROVIDER '{s.llm_provider}'.")


# ---------- reply parsing helpers ----------
def parse_llm_json(raw: str) -> dict:
    """Parse the model's reply into {supported, answer, explanation, key_points}, tolerating code fences."""
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", (raw or "").strip())
    candidates = [text]
    braces = re.search(r"\{.*\}", text, re.S)
    if braces:
        candidates.append(braces.group(0))
    data = None
    for candidate in candidates:
        try:
            data = json.loads(candidate)
            break
        except json.JSONDecodeError:
            continue
    if not isinstance(data, dict):
        # The model ignored the format; keep its text rather than fail the student's request.
        return {"supported": bool(text), "answer": text, "explanation": "", "key_points": []}
    points = data.get("key_points") or []
    return {
        "supported": bool(data.get("supported", True)),
        "answer": str(data.get("answer") or "").strip(),
        "explanation": str(data.get("explanation") or "").strip(),
        "key_points": [str(p).strip() for p in points if str(p).strip()] if isinstance(points, list) else [],
    }


def strip_invalid_citations(text: str, max_n: int) -> str:
    """Remove [n] markers that don't correspond to a passage that was actually retrieved."""
    def keep(m):
        return m.group(0) if 1 <= int(m.group(1)) <= max_n else ""
    return re.sub(r"\[(\d+)\]", keep, text)


def cited_numbers(*texts: str) -> set[int]:
    return {int(n) for t in texts for n in re.findall(r"\[(\d+)\]", t)}
