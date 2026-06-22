#!/usr/bin/env python3
"""
TrendScout Agent
Fetches trending topics for all 3 niches from RSS, Reddit, YouTube trending, Google Trends.
Outputs: JSON list of scored topics → topics_queue.json
"""
import json, time, hashlib, os, logging
from datetime import datetime, timedelta
import feedparser
import requests
from pytrends.request import TrendReq
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [TrendScout] %(message)s")
log = logging.getLogger(__name__)

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
SEEN_FILE = DATA_DIR / "seen_topics.json"
QUEUE_FILE = DATA_DIR / "topics_queue.json"

NICHES = {
    "ai_tech": {
        "rss": [
            "https://feeds.feedburner.com/TechCrunch",
            "https://www.theverge.com/rss/index.xml",
            "https://venturebeat.com/feed/",
            "https://tldr.tech/api/rss/ai",
            "https://aiweekly.co/issues.rss",
            "https://huggingface.co/blog/feed.xml",
        ],
        "reddit": ["artificial", "MachineLearning", "ChatGPT", "singularity"],
        "pytrends_kw": ["AI tools 2026", "ChatGPT", "automation software", "AI agent"],
        "script_template": "5 {topic} that will blow your mind in 2026",
    },
    "home_cleaning": {
        "rss": [
            "https://www.goodhousekeeping.com/rss/all.rss",
            "https://www.cleaninginstitute.org/feed",
            "https://www.apartmenttherapy.com/main.rss",
        ],
        "reddit": ["CleaningTips", "HomeImprovement", "lifehacks", "tidying"],
        "pytrends_kw": ["cleaning hacks", "satisfying cleaning", "home organization", "deep clean"],
        "script_template": "Satisfying {topic} transformation you won't believe",
    },
    "money_mindset": {
        "rss": [
            "https://www.moneysavingexpert.com/feed/",
            "https://feeds.feedburner.com/businessinsider",
            "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml",
            "https://www.investopedia.com/feedbuilder/feed/getfeed?feedName=rss_articles",
        ],
        "reddit": ["personalfinance", "financialindependence", "sidehustle", "Entrepreneur"],
        "pytrends_kw": ["side hustle 2026", "make money online", "passive income", "budgeting tips"],
        "script_template": "3 money habits that {topic} (most people ignore this)",
    },
}

REDDIT_HEADERS = {"User-Agent": "MPTAgent/1.0 (automated content research)"}


def load_seen() -> set:
    if SEEN_FILE.exists():
        return set(json.loads(SEEN_FILE.read_text()))
    return set()


def save_seen(seen: set):
    SEEN_FILE.write_text(json.dumps(list(seen)))


def topic_hash(text: str) -> str:
    return hashlib.md5(text.lower().strip().encode()).hexdigest()[:12]


def fetch_rss_topics(urls: list, niche: str) -> list:
    topics = []
    for url in urls:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:10]:
                title = entry.get("title", "").strip()
                if len(title) > 10:
                    topics.append({"title": title, "source": "rss", "niche": niche, "url": entry.get("link","")})
        except Exception as e:
            log.warning(f"RSS fetch failed {url}: {e}")
    return topics


def fetch_reddit_topics(subreddits: list, niche: str) -> list:
    topics = []
    for sub in subreddits:
        try:
            url = f"https://www.reddit.com/r/{sub}/hot.json?limit=10"
            r = requests.get(url, headers=REDDIT_HEADERS, timeout=10)
            data = r.json()
            for post in data.get("data", {}).get("children", []):
                d = post["data"]
                if d.get("score", 0) > 100 and not d.get("over_18", False):
                    topics.append({"title": d["title"], "source": "reddit",
                                   "niche": niche, "score": d["score"],
                                   "url": f"https://reddit.com{d.get('permalink','')}"})
        except Exception as e:
            log.warning(f"Reddit fetch failed r/{sub}: {e}")
        time.sleep(1)
    return topics


def fetch_pytrends_topics(keywords: list, niche: str) -> list:
    topics = []
    try:
        pt = TrendReq(hl="en-US", tz=330)
        pt.build_payload(keywords[:5], timeframe="now 1-d", geo="US")
        related = pt.related_queries()
        for kw, data in related.items():
            if data and data.get("rising") is not None:
                rising = data["rising"]
                if rising is not None and len(rising):
                    for _, row in rising.head(5).iterrows():
                        topics.append({"title": str(row["query"]), "source": "pytrends",
                                       "niche": niche, "score": int(row.get("value", 0))})
    except Exception as e:
        log.warning(f"PyTrends failed for {niche}: {e}")
    return topics


def score_topic(t: dict) -> float:
    base = {"reddit": 1.5, "pytrends": 2.0, "rss": 1.0}.get(t.get("source","rss"), 1.0)
    score = t.get("score", 50)
    return base * min(score, 1000) / 100


def run_trend_scout():
    seen = load_seen()
    all_topics = []

    for niche, config in NICHES.items():
        log.info(f"Scouting niche: {niche}")
        raw = []
        raw += fetch_rss_topics(config["rss"], niche)
        raw += fetch_reddit_topics(config["reddit"], niche)
        raw += fetch_pytrends_topics(config["pytrends_kw"], niche)

        for t in raw:
            h = topic_hash(t["title"])
            if h not in seen:
                t["hash"] = h
                t["score_val"] = score_topic(t)
                t["template"] = config["script_template"]
                t["created_at"] = datetime.utcnow().isoformat()
                t["status"] = "pending"
                all_topics.append(t)
                seen.add(h)

    all_topics.sort(key=lambda x: x["score_val"], reverse=True)
    top = all_topics[:30]

    existing = json.loads(QUEUE_FILE.read_text()) if QUEUE_FILE.exists() else []
    QUEUE_FILE.write_text(json.dumps(existing + top, indent=2))
    save_seen(seen)
    log.info(f"TrendScout added {len(top)} new topics to queue.")
    return top


if __name__ == "__main__":
    topics = run_trend_scout()
    for t in topics[:5]:
        print(f"  [{t['niche']}] {t['title']} (score={t['score_val']:.1f})")
