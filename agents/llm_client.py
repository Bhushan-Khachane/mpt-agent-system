#!/usr/bin/env python3
"""
LLM Client — Gemini-only backend.

Required env var:
  GEMINI_API_KEY   — from https://aistudio.google.com/app/apikey (free tier)

Optional env var:
  GEMINI_MODEL   — default: gemini-2.0-flash
"""
import os, logging
log = logging.getLogger(__name__)

GEMINI_KEY   = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")


def generate(prompt: str, max_tokens: int = 400, temperature: float = 0.8) -> str:
    """Send a text-generation request to the Gemini API."""
    import requests
    if not GEMINI_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. "
            "Get a free key at https://aistudio.google.com/app/apikey"
        )
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent?key={GEMINI_KEY}"
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
