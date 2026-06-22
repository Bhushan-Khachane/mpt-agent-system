#!/usr/bin/env python3
"""
SEO Agent — Gemini-only
Generates optimised title, description, tags and hashtags via Gemini API.
"""
import json, logging
from pathlib import Path
from agents.llm_client import generate

logging.basicConfig(level=logging.INFO, format="%(asctime)s [SEOAgent] %(message)s")
log = logging.getLogger(__name__)

DATA_DIR   = Path("data")
QUEUE_FILE = DATA_DIR / "topics_queue.json"

SEO_PROMPT = """You are an expert YouTube/Instagram SEO specialist.
For the video topic: "{title}" in the niche: "{niche}"

Generate the following in JSON format only (no markdown fences, no explanation, valid JSON):
{{
  "youtube_title": "Optimised title under 60 chars with power word",
  "youtube_description": "3-4 sentence description with keywords, include 3 relevant hashtags at end",
  "youtube_tags": ["tag1","tag2","tag3","tag4","tag5","tag6","tag7","tag8"],
  "instagram_caption": "Catchy 1-2 sentence caption + 15 relevant hashtags",
  "pinterest_description": "SEO-rich 2 sentence pin description",
  "thumbnail_text": "Max 5 word bold text for thumbnail overlay"
}}"""


def generate_seo(topic: dict) -> dict:
    prompt = SEO_PROMPT.format(title=topic["title"], niche=topic.get("niche", "general"))
    raw    = generate(prompt, max_tokens=500, temperature=0.7)
    try:
        start    = raw.find("{")
        end      = raw.rfind("}") + 1
        seo_data = json.loads(raw[start:end])
    except Exception:
        seo_data = {
            "youtube_title":        topic["title"][:60],
            "youtube_description":  topic.get("script", "")[:200],
            "youtube_tags":         topic.get("search_terms", [])[:8],
            "instagram_caption":    topic["title"] + " #shorts #viral",
            "pinterest_description": topic["title"],
            "thumbnail_text":       topic["title"][:30],
        }
    topic["seo"]    = seo_data
    topic["status"] = "seo_ready"
    return topic


def run_seo_agent(batch_size: int = 5):
    if not QUEUE_FILE.exists():
        return
    queue = json.loads(QUEUE_FILE.read_text())
    ready = [t for t in queue if t.get("status") == "video_ready"][:batch_size]
    if not ready:
        log.info("No videos ready for SEO.")
        return
    for t in ready:
        log.info(f"Generating SEO for: {t['title'][:50]}")
        try:
            generate_seo(t)
            log.info("  SEO metadata ready")
        except Exception as e:
            log.error(f"  SEO failed: {e}")
            t["status"] = "seo_failed"
    QUEUE_FILE.write_text(json.dumps(queue, indent=2))


if __name__ == "__main__":
    run_seo_agent()
