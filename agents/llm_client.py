#!/usr/bin/env python3
"""
LLM Client — Gemini-only.
Key is read lazily inside generate() so it works even if env var
is set AFTER the module is first imported (common in Colab).
"""
import os, logging
log = logging.getLogger(__name__)

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

PLACEHOLDERS = {"", "YOUR_GEMINI_API_KEY", "GOOGLE_API_KEY", "AIza...", "your_gemini_api_key"}


def generate(prompt: str, max_tokens: int = 400, temperature: float = 0.8) -> str:
    """Send a text-generation request to the Gemini API."""
    import requests
    # Read key lazily so Colab env vars set after import still work
    key   = os.environ.get("GEMINI_API_KEY", "")
    model = os.environ.get("GEMINI_MODEL", GEMINI_MODEL)

    if not key or key in PLACEHOLDERS:
        raise RuntimeError(
            "GEMINI_API_KEY is not set or still has the placeholder value.\n"
            "Get a free key at: https://aistudio.google.com/app/apikey"
        )

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={key}"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "maxOutputTokens": max_tokens,
            "temperature": temperature,
        },
    }
    r = requests.post(url, json=payload, timeout=30)
    r.raise_for_status()
    data = r.json()
    return data["candidates"][0]["content"]["parts"][0]["text"].strip()
