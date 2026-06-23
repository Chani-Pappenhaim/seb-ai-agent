"""
AI calls via Google Gemini (free tier) — new google-genai package (REST, not gRPC).
Fixes SSL certificate errors that occurred with the old google-generativeai package.
"""

import time
from google import genai
from google.genai import types
from config import Settings

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=Settings["api_key"])
    return _client


# ── System prompts — minimal to save tokens ───────────────────────────────────

_SYSTEM: dict[str, str] = {
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

_MAX_TOKENS: dict[str, int] = {
    "ASK":      250,
    "SOLVE":    600,
    "FIX":      600,
    "ASKALL":   300,
    "SOLVEALL": 800,
}


def ask_ai(tag_type: str, content: str, context: str = "") -> str:
    """Call Gemini and return response text."""
    system = _SYSTEM.get(tag_type, _SYSTEM["ASK"])
    max_tok = _MAX_TOKENS.get(tag_type, 300)

    if tag_type == "FIX" and context:
        if len(context) > 1500:
            context = context[-1500:]
        user_msg = f"Code:\n{context}\n\nFix instruction: {content}"
    else:
        user_msg = content

    if not user_msg.strip():
        raise ValueError("empty request")

    for attempt in range(3):
        try:
            response = _get_client().models.generate_content(
                model=Settings.get("model", "gemini-2.0-flash-lite"),
                contents=user_msg,
                config=types.GenerateContentConfig(
                    system_instruction=system,
                    max_output_tokens=max_tok,
                    temperature=0.3,
                ),
            )
            return response.text.strip()
        except Exception as e:
            if "429" in str(e) and attempt < 2:
                print(f"[AI] Rate limit — ממתין 15 שניות... (ניסיון {attempt+1}/3)")
                time.sleep(15)
            else:
                raise
