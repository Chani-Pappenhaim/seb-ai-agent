"""
AI Provider Management — Unified interface for multiple LLM providers.
Supports: Google Gemini, Groq, Mistral (with automatic provider detection).
"""

import time
import threading
from abc import ABC, abstractmethod
from config import Settings
from constants import RETRY_ATTEMPTS, RETRY_WAIT_SECONDS

# ── System Prompts ────────────────────────────────────────────────────────────

SYSTEM_PROMPTS = {
    "ASKALL": (
        "You are a programming tutor. Answer in Hebrew. Be concise: 3-5 sentences. "
        "The user will give you their full code followed by a question. Answer the question about the code."
    ),
    "SOLVEALL": (
        "You are a code generator. "
        "The user will give you the full exercise text and existing code. "
        "Output ONLY the complete solution code. No prose, no markdown fences."
    ),
    "ASK": (
        "You are a programming tutor. Answer in Hebrew. "
        "Be concise: 2-4 sentences. "
        "Give hints and explanations only — never write a full solution or complete code."
    ),
    "SOLVE": (
        "You are a code generator. "
        "Output ONLY the code. No prose, no markdown fences. "
        "Use the language or framework the student specifies."
    ),
    "FIX": (
        "You are a code debugger. "
        "Output ONLY the corrected complete code. No prose, no explanation."
    ),
}

MAX_TOKENS = {
    "ASK":      250,
    "SOLVE":    600,
    "FIX":      600,
    "ASKALL":   300,
    "SOLVEALL": 800,
}

# ── Provider Detection ────────────────────────────────────────────────────────

def detect_provider() -> str:
    """Automatically detect AI provider based on API key format."""
    explicit = Settings.get("provider", "").lower()
    if explicit in ("groq", "gemini", "mistral"):
        return explicit

    key = Settings.get("api_key", "")
    if key.startswith("gsk_"):
        return "groq"
    if key.startswith(("AIzaSy", "AQ.")):
        return "gemini"
    return "mistral"


# ── Base Provider Class ────────────────────────────────────────────────────────

class AIProvider(ABC):
    """Abstract base class for AI providers. Handles the shared retry loop."""

    @abstractmethod
    def _request(self, tag_type: str, user_msg: str):
        """
        Perform one attempt at the underlying API call.
        Must raise on failure. May raise RateLimitError to trigger a retry.
        """
        pass

    def generate(self, tag_type: str, user_msg: str) -> str:
        """Generate an AI response, retrying on rate limits."""
        for attempt in range(1, RETRY_ATTEMPTS + 1):
            try:
                return self._request(tag_type, user_msg)
            except RateLimitError:
                if attempt < RETRY_ATTEMPTS:
                    print(f"[AI] Rate limit — ממתין {RETRY_WAIT_SECONDS} שניות... (ניסיון {attempt}/{RETRY_ATTEMPTS})")
                    time.sleep(RETRY_WAIT_SECONDS)
                else:
                    raise


class RateLimitError(Exception):
    """Raised by a provider's _request() to signal a 429 (triggers retry)."""
    pass


def _system_and_limit(tag_type: str):
    system = SYSTEM_PROMPTS.get(tag_type, SYSTEM_PROMPTS["ASK"])
    max_tokens = MAX_TOKENS.get(tag_type, 300)
    return system, max_tokens


# ── Gemini Provider ────────────────────────────────────────────────────────────

class GeminiProvider(AIProvider):
    """Google Gemini AI provider."""

    def __init__(self):
        self.client = None

    def _get_client(self):
        """Lazy-load Gemini client."""
        if self.client is None:
            try:
                from google import genai
            except ImportError:
                raise ImportError(
                    "google-genai not installed. "
                    "Install with: pip install google-genai"
                )
            self.client = genai.Client(api_key=Settings["api_key"])
        return self.client

    def _request(self, tag_type: str, user_msg: str) -> str:
        from google.genai import types

        client = self._get_client()
        system, max_tokens = _system_and_limit(tag_type)
        model = Settings.get("model", "gemini-2.0-flash-lite")

        try:
            response = client.models.generate_content(
                model=model,
                contents=user_msg,
                config=types.GenerateContentConfig(
                    system_instruction=system,
                    max_output_tokens=max_tokens,
                    temperature=0.3,
                ),
            )
            return response.text.strip()
        except Exception as e:
            if "429" in str(e):
                raise RateLimitError(str(e)) from e
            raise


# ── Groq Provider ────────────────────────────────────────────────────────────

class GroqProvider(AIProvider):
    """Groq AI provider."""

    def __init__(self):
        self.client = None

    def _get_client(self):
        """Lazy-load Groq client."""
        if self.client is None:
            try:
                from groq import Groq
            except ImportError:
                raise ImportError(
                    "groq not installed. "
                    "Install with: pip install groq"
                )
            self.client = Groq(api_key=Settings["api_key"])
        return self.client

    def _request(self, tag_type: str, user_msg: str) -> str:
        client = self._get_client()
        system, max_tokens = _system_and_limit(tag_type)
        model = Settings.get("model", "llama-3.3-70b-versatile")

        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_msg},
                ],
                max_tokens=max_tokens,
                temperature=0.3,
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            if "429" in str(e):
                raise RateLimitError(str(e)) from e
            raise


# ── Mistral Provider ────────────────────────────────────────────────────────

class MistralProvider(AIProvider):
    """Mistral AI provider."""

    def _request(self, tag_type: str, user_msg: str) -> str:
        try:
            import requests
        except ImportError:
            raise ImportError(
                "requests not installed. "
                "Install with: pip install requests"
            )

        system, max_tokens = _system_and_limit(tag_type)
        model = Settings.get("model", "mistral-small-latest")

        resp = requests.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {Settings['api_key']}",
                "Content-Type": "application/json"
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_msg}
                ],
                "max_tokens": max_tokens,
                "temperature": 0.3
            },
            timeout=30,
        )

        if resp.status_code == 429:
            raise RateLimitError(f"429: {resp.text}")

        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()


# ── Provider Factory ────────────────────────────────────────────────────────

_PROVIDER_CLASSES = {
    "gemini": GeminiProvider,
    "groq": GroqProvider,
    "mistral": MistralProvider,
}

_provider_instances = {}
_provider_lock = threading.Lock()


def get_provider() -> AIProvider:
    """Get the configured AI provider instance (thread-safe lazy singleton)."""
    provider_name = detect_provider()

    with _provider_lock:
        if provider_name not in _provider_instances:
            _provider_instances[provider_name] = _PROVIDER_CLASSES[provider_name]()
        return _provider_instances[provider_name]


def ask_ai(tag_type: str, content: str, context: str = "") -> str:
    """
    Send a request to the configured AI provider.

    Args:
        tag_type: Type of tag (ASK, SOLVE, FIX, etc.)
        content: Main content of the request
        context: Optional context (e.g., code to fix). Caller is responsible
            for truncating context to a reasonable size before calling.

    Returns:
        AI response text
    """
    if tag_type == "FIX" and context:
        user_msg = f"Code:\n{context}\n\nFix instruction: {content}"
    else:
        user_msg = content

    if not user_msg.strip():
        raise ValueError("Request cannot be empty")

    provider = get_provider()
    return provider.generate(tag_type, user_msg)
