#!/usr/bin/env python3
"""
LLM Client — Gemini REST API only.
Key is read LAZILY inside generate() so it works in Colab
even when the module is imported before the env var is set.
"""
import os
import logging

log = logging.getLogger(__name__)

_PLACEHOLDERS = {"", "AIza...", "YOUR_GEMINI_API_KEY", "your_gemini_api_key"}


def generate(prompt: str, max_tokens: int = 400, temperature: float = 0.8) -> str:
    import requests

    key   = os.environ.get("GEMINI_API_KEY", "").strip()
    model = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash").strip()

    if not key or key in _PLACEHOLDERS:
        raise RuntimeError(
            "GEMINI_API_KEY is not set or still has the placeholder value.\n"
            "Get a FREE key at: https://aistudio.google.com/app/apikey"
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
    resp = requests.post(url, json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
