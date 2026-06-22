#!/usr/bin/env python3
"""
ScriptWriter Agent — Gemini-only
Generates MPT-ready scripts via Gemini API.
DATA_DIR is resolved relative to this file so it works regardless of CWD.
"""
import json
import logging
from pathlib import Path

from agents.llm_client import generate

logging.basicConfig(level=logging.INFO, format="%(asctime)s [ScriptWriter] %(message)s")
log = logging.getLogger(__name__)

# Always resolved as: repo_root/data/
DATA_DIR   = Path(__file__).resolve().parent.parent / "data"
QUEUE_FILE = DATA_DIR / "topics_queue.json"

# For longer final videos, we explicitly target 120–180 words per script.
# MoneyPrinterTurbo derives audio duration directly from script length, so a
# ~150-word script gives ~25–35s of TTS audio instead of ~5–10s.
NICHE_PROMPTS = {
    "ai_tech": (
        'You are a viral YouTube Shorts scriptwriter for the AI & Automation niche.\n'
        'Write a 120-180 word narration script for a SHORT video titled: "{title}"\n'
        'Rules:\n'
        '- Strong hook in the first sentence (e.g. "Nobody talks about...")\n'
        '- 4-6 punchy points, each 1-2 sentences, concrete and practical\n'
        '- End with call to action: "Follow for more AI tools"\n'
        '- Conversational US English, no heavy jargon\n'
        '- NO hashtags, NO emojis, NO scene directions\n'
        'Output ONLY the script text, nothing else.'
    ),
    "home_cleaning": (
        'You are a viral YouTube Shorts scriptwriter for the Home Cleaning & Satisfying niche.\n'
        'Write a 80-140 word narration script for a SHORT video titled: "{title}"\n'
        'Rules:\n'
        '- Open with a strong visual cue (e.g. "Watch this disgusting sink become spotless in 15 seconds")\n'
        '- 3-5 short, vivid lines timed to different cleaning moments\n'
        '- Keep sentences very short; let the stock footage do most of the work\n'
        '- End with: "Save this for later!"\n'
        '- US English, upbeat tone\n'
        '- NO hashtags, NO emojis, NO scene directions\n'
        'Output ONLY the script text, nothing else.'
    ),
    "money_mindset": (
        'You are a viral YouTube Shorts scriptwriter for the Money Mindset & Side Hustle niche.\n'
        'Write a 130-190 word narration script for a SHORT video titled: "{title}"\n'
        'Rules:\n'
        '- Hook: surprising money stat or question in the first sentence\n'
        '- 4-6 actionable tips or mindset shifts, each 1 concise sentence\n'
        '- Use simple language that a 15-year-old can understand\n'
        '- End with: "Which one will you try first? Comment below."\n'
        '- US English, motivational but grounded (no get-rich-quick claims)\n'
        '- NO hashtags, NO emojis, NO scene directions\n'
        'Output ONLY the script text, nothing else.'
    ),
}

KEYWORD_MAP = {
    "ai_tech":       ["AI technology", "artificial intelligence", "computer screen",
                      "digital data", "coding", "automation", "futuristic technology"],
    "home_cleaning": ["cleaning house", "sparkling clean kitchen", "pressure washing",
                      "soapy foam", "organized home", "scrubbing floor", "satisfying clean"],
    "money_mindset": ["business success", "counting money", "laptop working",
                      "entrepreneur", "stock market", "financial freedom"],
}


def generate_script(topic: dict) -> dict:
    niche  = topic.get("niche", "ai_tech")
    tmpl   = NICHE_PROMPTS.get(niche, NICHE_PROMPTS["ai_tech"])
    prompt = tmpl.format(title=topic["title"])
    # Allow longer outputs so scripts can drive ~20–40s videos
    script = generate(prompt, max_tokens=400, temperature=0.8)
    topic["script"]        = script
    topic["video_subject"] = topic["title"]
    # comma-joined string for MPT CLI --video-terms
    topic["video_terms"]   = ",".join(KEYWORD_MAP.get(niche, KEYWORD_MAP["ai_tech"])[:5])
    topic["status"]        = "scripted"
    return topic


def run_script_writer(batch_size: int = 5) -> int:
    if not QUEUE_FILE.exists():
        log.warning("No topics queue found at %s", QUEUE_FILE)
        return 0
    queue   = json.loads(QUEUE_FILE.read_text())
    pending = [t for t in queue if t.get("status") == "pending"][:batch_size]
    if not pending:
        log.info("No pending topics to script.")
        return 0
    for t in pending:
        log.info("Writing script for: %s", t["title"])
        try:
            generate_script(t)
            log.info("  Script ready (%d chars)", len(t["script"]))
        except Exception as exc:
            log.error("  Failed: %s", exc)
            t["status"] = "script_failed"
    QUEUE_FILE.write_text(json.dumps(queue, indent=2))
    scripted = [t for t in pending if t.get("status") == "scripted"]
    log.info("ScriptWriter done: %d/%d scripted.", len(scripted), len(pending))
    return len(scripted)


if __name__ == "__main__":
    run_script_writer(batch_size=5)
