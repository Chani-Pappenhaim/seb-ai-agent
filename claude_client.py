"""
AI calls — supports Mistral, Groq, and Google Gemini.
Provider is selected automatically based on the api_key format or 'provider' field in settings.json.
  Groq key    starts with  gsk_
  Gemini key  starts with  AIzaSy or AQ.
  Mistral key — everything else (set provider: "mistral" to be explicit)
"""

import time
from config import Settings

_groq_client    = None
_gemini_client  = None
_mistral_client = None


def _provider() -> str:
    explicit = Settings.get("provider", "").lower()
    if explicit in ("groq", "gemini", "mistral"):
        return explicit
    key = Settings.get("api_key", "")
    if key.startswith("gsk_"):
        return "groq"
    if key.startswith(("AIzaSy", "AQ.")):
        return "gemini"
    return "mistral"


def _get_groq():
    global _groq_client
    if _groq_client is None:
        from groq import Groq
        _groq_client = Groq(api_key=Settings["api_key"])
    return _groq_client




def _get_gemini():
    global _gemini_client
    if _gemini_client is None:
        from google import genai
        _gemini_client = genai.Client(api_key=Settings["api_key"])
    return _gemini_client


# ── System prompts ────────────────────────────────────────────────────────────

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


def _call_groq(tag_type: str, user_msg: str) -> str:
    client   = _get_groq()
    system   = _SYSTEM.get(tag_type, _SYSTEM["ASK"])
    max_tok  = _MAX_TOKENS.get(tag_type, 300)
    model    = Settings.get("model", "llama-3.3-70b-versatile")

    for attempt in range(3):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system",    "content": system},
                    {"role": "user",      "content": user_msg},
                ],
                max_tokens=max_tok,
                temperature=0.3,
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            if "429" in str(e) and attempt < 2:
                print(f"[AI] Rate limit — ממתין 15 שניות... (ניסיון {attempt+1}/3)")
                time.sleep(15)
            else:
                raise


def _call_gemini(tag_type: str, user_msg: str) -> str:
    from google.genai import types
    client  = _get_gemini()
    system  = _SYSTEM.get(tag_type, _SYSTEM["ASK"])
    max_tok = _MAX_TOKENS.get(tag_type, 300)
    model   = Settings.get("model", "gemini-2.0-flash")

    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model=model,
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


def _call_mistral(tag_type: str, user_msg: str) -> str:
    import requests
    system  = _SYSTEM.get(tag_type, _SYSTEM["ASK"])
    max_tok = _MAX_TOKENS.get(tag_type, 300)
    model   = Settings.get("model", "mistral-small-latest")

    for attempt in range(3):
        try:
            resp = requests.post(
                "https://api.mistral.ai/v1/chat/completions",
                headers={"Authorization": f"Bearer {Settings['api_key']}",
                         "Content-Type": "application/json"},
                json={"model": model,
                      "messages": [{"role": "system", "content": system},
                                   {"role": "user",   "content": user_msg}],
                      "max_tokens": max_tok,
                      "temperature": 0.3},
                timeout=30,
            )
            if resp.status_code == 429 and attempt < 2:
                print(f"[AI] Rate limit — ממתין 15 שניות... (ניסיון {attempt+1}/3)")
                time.sleep(15)
                continue
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            if attempt < 2 and "429" in str(e):
                print(f"[AI] Rate limit — ממתין 15 שניות... (ניסיון {attempt+1}/3)")
                time.sleep(15)
            else:
                raise


def ask_ai(tag_type: str, content: str, context: str = "") -> str:
    if tag_type == "FIX" and context:
        if len(context) > 1500:
            context = context[-1500:]
        user_msg = f"Code:\n{context}\n\nFix instruction: {content}"
    else:
        user_msg = content

    if not user_msg.strip():
        raise ValueError("empty request")

    provider = _provider()
    if provider == "groq":
        return _call_groq(tag_type, user_msg)
    elif provider == "mistral":
        return _call_mistral(tag_type, user_msg)
    else:
        return _call_gemini(tag_type, user_msg)
