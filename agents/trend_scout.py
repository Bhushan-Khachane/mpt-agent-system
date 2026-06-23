#!/usr/bin/env python3
"""
TrendScout Agent — RSS + curated fallback (no Reddit, no blocking).
Reddit JSON is blocked on Colab IPs. PyTrends silently skipped on 429.

DATA_DIR is resolved relative to THIS FILE so it always points to
/content/mpt-agent-system/data/ regardless of CWD at import time.
"""
import json
import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path

import feedparser

logging.basicConfig(level=logging.INFO, format="%(asctime)s [TrendScout] %(message)s")
log = logging.getLogger(__name__)

# ✅ Always resolves to repo_root/data/ regardless of CWD
REPO_ROOT  = Path(__file__).resolve().parent.parent
DATA_DIR   = REPO_ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
SEEN_FILE  = DATA_DIR / "seen_topics.json"
QUEUE_FILE = DATA_DIR / "topics_queue.json"

NICHES = {
    "ai_tech": {
        "rss": [
            "https://feeds.feedburner.com/TechCrunch",
            "https://www.theverge.com/rss/index.xml",
            "https://venturebeat.com/feed/",
            "https://tldr.tech/api/rss/ai",
        ],
        "fallback": [
            "5 AI tools that will replace your entire workflow",
            "ChatGPT vs Gemini which is smarter in 2026",
            "How AI agents are changing the way we work",
            "Top 3 free AI tools nobody talks about",
            "AI automation tricks that save 2 hours a day",
            "The AI tool every small business needs right now",
            "3 AI side hustles making 5k per month",
            "How to build an AI agent in 10 minutes",
            "Best AI tools for content creators in 2026",
            "How to automate your entire workflow with AI",
        ],
        "pytrends_kw": ["AI tools 2026", "ChatGPT", "AI agent"],
        "script_template": "5 {topic} that will blow your mind in 2026",
    },
    "home_cleaning": {
        "rss": [
            "https://www.goodhousekeeping.com/rss/all.rss",
            "https://www.apartmenttherapy.com/main.rss",
        ],
        "fallback": [
            "Watch this filthy oven become spotless in 60 seconds",
            "The satisfying bathroom deep clean you need to see",
            "3 cleaning hacks that actually work",
            "How to clean your whole house in 30 minutes",
            "This pressure washing video is oddly satisfying",
            "The one cleaning product that does everything",
            "How to deep clean a couch in under 10 minutes",
            "Morning cleaning routine that keeps your home spotless",
            "Satisfying kitchen deep clean transformation",
            "How to remove stains that never come out",
        ],
        "pytrends_kw": ["cleaning hacks", "satisfying cleaning", "deep clean"],
        "script_template": "Satisfying {topic} transformation you wont believe",
    },
    "money_mindset": {
        "rss": [
            "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml",
            "https://www.investopedia.com/feedbuilder/feed/getfeed?feedName=rss_articles",
        ],
        "fallback": [
            "3 money habits that separate rich from broke",
            "The side hustle making 3k per month with 2 hours a week",
            "Why most people stay broke and how to fix it",
            "5 passive income ideas you can start with zero dollars",
            "The budgeting method that actually works",
            "How to make your first 1000 dollars online",
            "3 things rich people do that broke people dont",
            "The simplest way to build wealth from scratch",
            "How to save money when you have none left",
            "Compound interest explained in 60 seconds",
        ],
        "pytrends_kw": ["side hustle 2026", "passive income", "make money online"],
        "script_template": "3 money habits that {topic} most people ignore this",
    },
}


def load_seen() -> set:
    if SEEN_FILE.exists():
        try:
            data = json.loads(SEEN_FILE.read_text())
            return set(data) if isinstance(data, list) else set(data.keys())
        except Exception:
            pass
    return set()


def save_seen(seen: set):
    SEEN_FILE.write_text(json.dumps(list(seen)))


def topic_hash(text: str) -> str:
    return hashlib.md5(text.lower().strip().encode()).hexdigest()[:12]


def fetch_rss(urls: list, niche: str) -> list:
    topics = []
    for url in urls:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:8]:
                title = entry.get("title", "").strip()
                if len(title) > 10:
                    topics.append({
                        "title":  title,
                        "source": "rss",
                        "niche":  niche,
                        "score":  200,
                        "url":    entry.get("link", ""),
                    })
        except Exception as exc:
            log.warning("RSS failed %s: %s", url, exc)
    return topics


def fetch_pytrends(keywords: list, niche: str) -> list:
    topics = []
    try:
        from pytrends.request import TrendReq
        pt = TrendReq(hl="en-US", tz=330, timeout=(5, 10), retries=1, backoff_factor=0.3)
        pt.build_payload(keywords[:3], timeframe="now 1-d", geo="US")
        for kw, data in pt.related_queries().items():
            if data and data.get("rising") is not None:
                rising = data["rising"]
                if rising is not None and len(rising):
                    for _, row in rising.head(3).iterrows():
                        topics.append({
                            "title":  str(row["query"]),
                            "source": "pytrends",
                            "niche":  niche,
                            "score":  int(row.get("value", 50)),
                        })
    except Exception as exc:
        log.info("PyTrends skipped (%s): %s", niche, type(exc).__name__)
    return topics


def inject_fallback(niche: str, config: dict, seen: set, existing_titles: set) -> list:
    topics = []
    for title in config["fallback"]:
        h = topic_hash(title)
        if h not in seen and title.lower() not in existing_titles:
            topics.append({"title": title, "source": "fallback", "niche": niche, "score": 100})
    return topics


def score_topic(t: dict) -> float:
    base = {"pytrends": 2.0, "rss": 1.2, "fallback": 0.8}.get(t.get("source", "rss"), 1.0)
    return base * min(t.get("score", 50), 1000) / 100


def run_trend_scout(niche: str | None = None) -> list:
    """Run TrendScout for either all niches or a single niche.

    If niche is provided, only that niche key from NICHES is used. This lets the
    Colab notebook pass a manual niche instead of scouting everything.
    """
    log.info("DATA_DIR = %s", DATA_DIR)
    seen     = load_seen()
    existing = json.loads(QUEUE_FILE.read_text()) if QUEUE_FILE.exists() else []
    existing_titles = {t["title"].lower() for t in existing}
    all_topics: list = []

    niches_to_run = [niche] if niche else list(NICHES.keys())
    for n in niches_to_run:
        config = NICHES.get(n)
        if not config:
            log.warning("Unknown niche: %s", n)
            continue
        log.info("Scouting niche: %s", n)
        raw  = fetch_rss(config["rss"], n)
        raw += fetch_pytrends(config.get("pytrends_kw", []), n)
        raw += inject_fallback(n, config, seen, existing_titles)
        for t in raw:
            h = topic_hash(t["title"])
            if h not in seen:
                t["hash"]       = h
                t["score_val"]  = score_topic(t)
                t["template"]   = config["script_template"]
                t["created_at"] = datetime.now(timezone.utc).isoformat()
                t["status"]     = "pending"
                all_topics.append(t)
                seen.add(h)

    all_topics.sort(key=lambda x: x["score_val"], reverse=True)
    top = all_topics[:30]
    QUEUE_FILE.write_text(json.dumps(existing + top, indent=2))
    save_seen(seen)
    log.info("TrendScout added %d new topics to queue. Queue file: %s", len(top), QUEUE_FILE)
    return top


if __name__ == "__main__":
    for t in run_trend_scout()[:5]:
        print(f"  [{t['niche']}] {t['title']} (score={t['score_val']:.1f})")
