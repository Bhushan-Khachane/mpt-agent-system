#!/usr/bin/env python3
"""
LLM Client — unified interface for Ollama, HuggingFace Gemma (Colab), and Gemini API.

Priority order (auto-detected from env vars):
  1. HF_GEMMA   — HuggingFace Transformers (Gemma on Colab GPU / local)
  2. OLLAMA     — local Ollama server
  3. GEMINI     — Google Gemini API (cloud fallback)

Set LLM_BACKEND=hf_gemma | ollama | gemini to force a specific backend.
"""
import os, logging, json
log = logging.getLogger(__name__)

LLM_BACKEND = os.getenv("LLM_BACKEND", "").lower()   # force override
HF_MODEL_ID  = os.getenv("HF_MODEL_ID",  "google/gemma-3-4b-it")
HF_TOKEN     = os.getenv("HF_TOKEN",     "")          # HuggingFace token for gated models
OLLAMA_URL   = os.getenv("OLLAMA_URL",   "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:4b")
GEMINI_KEY   = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

# ── Shared HF pipeline (loaded once, reused across calls) ─────────────────────
_hf_pipeline = None

def _load_hf_pipeline():
    global _hf_pipeline
    if _hf_pipeline is not None:
        return _hf_pipeline
    try:
        import torch
        from transformers import pipeline, BitsAndBytesConfig
        log.info(f"Loading HuggingFace model: {HF_MODEL_ID}")
        kwargs = {
            "model": HF_MODEL_ID,
            "task": "text-generation",
            "device_map": "auto",
            "torch_dtype": torch.bfloat16,
        }
        if HF_TOKEN:
            kwargs["token"] = HF_TOKEN
        # 4-bit quant for T4 free tier (fits in 15 GB VRAM)
        try:
            from transformers import BitsAndBytesConfig
            kwargs["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.bfloat16,
            )
        except Exception:
            pass  # bitsandbytes not available, use fp16
        _hf_pipeline = pipeline(**kwargs)
        log.info("HF pipeline ready.")
        return _hf_pipeline
    except Exception as e:
        log.error(f"Failed to load HF pipeline: {e}")
        raise


def _call_hf(prompt: str, max_new_tokens: int = 400, temperature: float = 0.8) -> str:
    pipe = _load_hf_pipeline()
    messages = [{"role": "user", "content": prompt}]
    result = pipe(
        messages,
        max_new_tokens=max_new_tokens,
        temperature=temperature,
        do_sample=True,
        pad_token_id=pipe.tokenizer.eos_token_id,
    )
    # pipeline returns list of dicts; extract assistant reply
    out = result[0].get("generated_text", "")
    if isinstance(out, list):
        # chat format: last message is assistant
        for msg in reversed(out):
            if isinstance(msg, dict) and msg.get("role") == "assistant":
                return msg["content"].strip()
    return str(out).strip()


def _call_ollama(prompt: str, max_tokens: int = 400, temperature: float = 0.8) -> str:
    import requests
    payload = {"model": OLLAMA_MODEL, "prompt": prompt, "stream": False,
               "options": {"temperature": temperature, "num_predict": max_tokens}}
    r = requests.post(OLLAMA_URL, json=payload, timeout=90)
    r.raise_for_status()
    return r.json().get("response", "").strip()


def _call_gemini(prompt: str, max_tokens: int = 400, temperature: float = 0.8) -> str:
    import requests
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": max_tokens, "temperature": temperature},
    }
    r = requests.post(url, json=payload, timeout=30)
    r.raise_for_status()
    return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()


def _detect_backend() -> str:
    if LLM_BACKEND:
        return LLM_BACKEND
    # auto-detect
    try:
        import torch
        import transformers  # noqa
        if torch.cuda.is_available() or os.path.exists("/content"):  # Colab
            return "hf_gemma"
    except ImportError:
        pass
    try:
        import requests
        r = requests.get(OLLAMA_URL.replace("/api/generate", "/api/tags"), timeout=3)
        if r.ok:
            return "ollama"
    except Exception:
        pass
    if GEMINI_KEY:
        return "gemini"
    return "ollama"  # default attempt


def generate(prompt: str, max_tokens: int = 400, temperature: float = 0.8) -> str:
    """Unified LLM call. Auto-selects backend unless LLM_BACKEND is set."""
    backend = _detect_backend()
    log.debug(f"LLM backend: {backend}")
    if backend == "hf_gemma":
        return _call_hf(prompt, max_new_tokens=max_tokens, temperature=temperature)
    elif backend == "ollama":
        return _call_ollama(prompt, max_tokens=max_tokens, temperature=temperature)
    elif backend == "gemini":
        return _call_gemini(prompt, max_tokens=max_tokens, temperature=temperature)
    else:
        raise ValueError(f"Unknown LLM_BACKEND: {backend}")
