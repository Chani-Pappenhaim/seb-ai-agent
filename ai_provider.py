"""
AI Provider Management — Unified interface for multiple LLM providers.
Supports: Google Gemini, Groq, Mistral (with automatic provider detection).
"""

import time
from abc import ABC, abstractmethod
from config import Settings
from constants import RETRY_ATTEMPTS, RETRY_WAIT_SECONDS, FIX_CONTEXT_LIMIT

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
    """Abstract base class for AI providers."""

    @abstractmethod
    def generate(self, tag_type: str, user_msg: str) -> str:
        """Generate AI response."""
        pass

    def _log_rate_limit(self, attempt: int):
        """Log rate limit message."""
        print(f"[AI] Rate limit — ממתין 15 שניות... (ניסיון {attempt}/{RETRY_ATTEMPTS})")


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
                self.client = genai.Client(api_key=Settings["api_key"])
            except ImportError:
                raise ImportError(
                    "google-genai not installed. "
                    "Install with: pip install google-genai"
                )
        return self.client

    def generate(self, tag_type: str, user_msg: str) -> str:
        """Generate response via Gemini."""
        from google.genai import types

        client = self._get_client()
        system = SYSTEM_PROMPTS.get(tag_type, SYSTEM_PROMPTS["ASK"])
        max_tokens = MAX_TOKENS.get(tag_type, 300)
        model = Settings.get("model", "gemini-2.0-flash-lite")

        for attempt in range(1, RETRY_ATTEMPTS + 1):
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
                if "429" in str(e) and attempt < RETRY_ATTEMPTS:
                    self._log_rate_limit(attempt)
                    time.sleep(RETRY_WAIT_SECONDS)
                else:
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
                self.client = Groq(api_key=Settings["api_key"])
            except ImportError:
                raise ImportError(
                    "groq not installed. "
                    "Install with: pip install groq"
                )
        return self.client

    def generate(self, tag_type: str, user_msg: str) -> str:
        """Generate response via Groq."""
        client = self._get_client()
        system = SYSTEM_PROMPTS.get(tag_type, SYSTEM_PROMPTS["ASK"])
        max_tokens = MAX_TOKENS.get(tag_type, 300)
        model = Settings.get("model", "llama-3.3-70b-versatile")

        for attempt in range(1, RETRY_ATTEMPTS + 1):
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
                if "429" in str(e) and attempt < RETRY_ATTEMPTS:
                    self._log_rate_limit(attempt)
                    time.sleep(RETRY_WAIT_SECONDS)
                else:
                    raise


# ── Mistral Provider ────────────────────────────────────────────────────────

class MistralProvider(AIProvider):
    """Mistral AI provider."""

    def generate(self, tag_type: str, user_msg: str) -> str:
        """Generate response via Mistral."""
        try:
            import requests
        except ImportError:
            raise ImportError(
                "requests not installed. "
                "Install with: pip install requests"
            )

        system = SYSTEM_PROMPTS.get(tag_type, SYSTEM_PROMPTS["ASK"])
        max_tokens = MAX_TOKENS.get(tag_type, 300)
        model = Settings.get("model", "mistral-small-latest")

        for attempt in range(1, RETRY_ATTEMPTS + 1):
            try:
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

                if resp.status_code == 429 and attempt < RETRY_ATTEMPTS:
                    self._log_rate_limit(attempt)
                    time.sleep(RETRY_WAIT_SECONDS)
                    continue

                resp.raise_for_status()
                return resp.json()["choices"][0]["message"]["content"].strip()
            except Exception as e:
                if attempt < RETRY_ATTEMPTS and "429" in str(e):
                    self._log_rate_limit(attempt)
                    time.sleep(RETRY_WAIT_SECONDS)
                else:
                    raise


# ── Provider Factory ────────────────────────────────────────────────────────

_provider_instances = {
    "gemini": None,
    "groq": None,
    "mistral": None,
}


def get_provider() -> AIProvider:
    """Get the configured AI provider instance."""
    provider_name = detect_provider()

    if provider_name == "gemini":
        if _provider_instances["gemini"] is None:
            _provider_instances["gemini"] = GeminiProvider()
        return _provider_instances["gemini"]

    elif provider_name == "groq":
        if _provider_instances["groq"] is None:
            _provider_instances["groq"] = GroqProvider()
        return _provider_instances["groq"]

    else:  # mistral
        if _provider_instances["mistral"] is None:
            _provider_instances["mistral"] = MistralProvider()
        return _provider_instances["mistral"]


def ask_ai(tag_type: str, content: str, context: str = "") -> str:
    """
    Send a request to the configured AI provider.

    Args:
        tag_type: Type of tag (ASK, SOLVE, FIX, etc.)
        content: Main content of the request
        context: Optional context (e.g., code to fix)

    Returns:
        AI response text
    """
    if tag_type == "FIX" and context:
        if len(context) > FIX_CONTEXT_LIMIT:
            context = context[-FIX_CONTEXT_LIMIT:]
        user_msg = f"Code:\n{context}\n\nFix instruction: {content}"
    else:
        user_msg = content

    if not user_msg.strip():
        raise ValueError("Request cannot be empty")

    provider = get_provider()
    return provider.generate(tag_type, user_msg)
