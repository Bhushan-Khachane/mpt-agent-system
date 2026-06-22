#!/usr/bin/env python3
"""
ScriptWriter Agent
Takes pending topics from queue, generates MPT-ready short video scripts via Ollama.
Updates topics_queue.json with script + video subject.
"""
import json, logging, os
from pathlib import Path
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s [ScriptWriter] %(message)s")
log = logging.getLogger(__name__)

DATA_DIR = Path("data")
QUEUE_FILE = DATA_DIR / "topics_queue.json"

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:4b")

NICHE_PROMPTS = {
    "ai_tech": """You are a viral YouTube Shorts scriptwriter for the AI & Automation niche.
Write a 50-70 word narration script for a SHORT video titled: "{title}"
Rules:
- Hook in first 3 words (e.g. "Nobody talks about...")
- 3 punchy points, each 1-2 sentences
- End with call to action: "Follow for more AI tools"
- Conversational, US English, no jargon
- NO hashtags in script
Output ONLY the script, nothing else.""",

    "home_cleaning": """You are a viral YouTube Shorts scriptwriter for the Home Cleaning & Satisfying niche.
Write a 30-50 word narration script for a SHORT video titled: "{title}"
Rules:
- Open with a satisfying visual description cue (e.g. "Watch this...")
- Very minimal words — let the stock footage do the work
- 2-3 short punchy sentences max
- End with: "Save this for later!"
- US English, upbeat tone
Output ONLY the script, nothing else.""",

    "money_mindset": """You are a viral YouTube Shorts scriptwriter for the Money Mindset & Side Hustle niche.
Write a 60-80 word narration script for a SHORT video titled: "{title}"
Rules:
- Hook: surprising money stat or question in first sentence
- 3 actionable tips or mindset shifts, each 1 sentence
- End with: "Which one will you try first? Comment below."
- US English, motivational but grounded
- NO financial advice disclaimers needed (keep it light)
Output ONLY the script, nothing else.""",
}

KEYWORD_MAP = {
    "ai_tech": ["AI technology", "artificial intelligence", "computer screen", "robot", "digital data", "coding", "automation", "futuristic technology"],
    "home_cleaning": ["cleaning house", "sparkling clean kitchen", "pressure washing", "soapy foam", "organized home", "scrubbing floor", "laundry", "satisfying clean"],
    "money_mindset": ["business success", "counting money", "laptop working", "city skyline", "entrepreneur", "stock market", "financial freedom", "productive morning"],
}


def call_ollama(prompt: str) -> str:
    payload = {"model": OLLAMA_MODEL, "prompt": prompt, "stream": False,
                "options": {"temperature": 0.8, "num_predict": 200}}
    r = requests.post(OLLAMA_URL, json=payload, timeout=60)
    r.raise_for_status()
    return r.json().get("response", "").strip()


def generate_script(topic: dict) -> dict:
    niche = topic.get("niche", "ai_tech")
    prompt_tmpl = NICHE_PROMPTS.get(niche, NICHE_PROMPTS["ai_tech"])
    prompt = prompt_tmpl.format(title=topic["title"])

    script = call_ollama(prompt)
    keywords = KEYWORD_MAP.get(niche, KEYWORD_MAP["ai_tech"])

    topic["script"] = script
    topic["video_subject"] = topic["title"]
    topic["search_terms"] = keywords
    topic["status"] = "scripted"
    return topic


def run_script_writer(batch_size: int = 5):
    if not QUEUE_FILE.exists():
        log.warning("No topics queue found.")
        return

    queue = json.loads(QUEUE_FILE.read_text())
    pending = [t for t in queue if t.get("status") == "pending"][:batch_size]

    if not pending:
        log.info("No pending topics to script.")
        return

    for t in pending:
        log.info(f"Writing script for: {t['title']}")
        try:
            generate_script(t)
            log.info(f"  Script ready ({len(t['script'])} chars)")
        except Exception as e:
            log.error(f"  Failed: {e}")
            t["status"] = "script_failed"

    QUEUE_FILE.write_text(json.dumps(queue, indent=2))
    scripted = [t for t in pending if t["status"] == "scripted"]
    log.info(f"ScriptWriter done: {len(scripted)}/{len(pending)} scripted.")


if __name__ == "__main__":
    run_script_writer(batch_size=5)
