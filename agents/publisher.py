#!/usr/bin/env python3
"""
Publisher Agent
Posts video + SEO metadata to YouTube Shorts, Instagram Reels, Facebook Reels.
Uses upload-post.com API (MPT native) or direct YouTube Data API v3.
"""
import json, logging, os, time
from pathlib import Path
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s [Publisher] %(message)s")
log = logging.getLogger(__name__)

DATA_DIR = Path("data")
QUEUE_FILE = DATA_DIR / "topics_queue.json"
MPT_API_URL = os.getenv("MPT_API_URL", "http://localhost:8080")

CHANNEL_MAP = {
    "ai_tech": {
        "youtube": os.getenv("YT_CHANNEL_AI", ""),
        "instagram": os.getenv("IG_ACCOUNT_AI", ""),
        "facebook": os.getenv("FB_PAGE_AI", ""),
    },
    "home_cleaning": {
        "youtube": os.getenv("YT_CHANNEL_CLEAN", ""),
        "instagram": os.getenv("IG_ACCOUNT_CLEAN", ""),
        "facebook": os.getenv("FB_PAGE_CLEAN", ""),
    },
    "money_mindset": {
        "youtube": os.getenv("YT_CHANNEL_MONEY", ""),
        "instagram": os.getenv("IG_ACCOUNT_MONEY", ""),
        "facebook": os.getenv("FB_PAGE_MONEY", ""),
    },
}


def post_via_mpt_api(topic: dict) -> dict:
    """Uses MPT's built-in upload-post.com integration."""
    niche = topic.get("niche", "ai_tech")
    seo = topic.get("seo", {})
    video_path = topic.get("video_path", "")

    payload = {
        "video_path": video_path,
        "title": seo.get("youtube_title", topic["title"]),
        "description": seo.get("youtube_description", ""),
        "tags": seo.get("youtube_tags", []),
        "platforms": ["youtube", "instagram"],
        "channel_ids": CHANNEL_MAP.get(niche, {}),
        "privacy": "public",
    }

    r = requests.post(f"{MPT_API_URL}/api/v1/upload", json=payload, timeout=120)
    r.raise_for_status()
    return r.json()


def post_to_youtube_direct(topic: dict) -> str:
    """Direct YouTube Data API v3 upload (fallback)."""
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from google.oauth2.credentials import Credentials

    niche = topic["niche"]
    seo = topic.get("seo", {})
    token_file = f"credentials/youtube_{niche}_token.json"
    if not Path(token_file).exists():
        raise FileNotFoundError(f"YouTube token missing: {token_file}")

    creds = Credentials.from_authorized_user_file(token_file)
    youtube = build("youtube", "v3", credentials=creds)

    body = {
        "snippet": {
            "title": seo.get("youtube_title", topic["title"])[:100],
            "description": seo.get("youtube_description", "")[:5000],
            "tags": seo.get("youtube_tags", [])[:500],
            "categoryId": "28",
        },
        "status": {"privacyStatus": "public", "madeForKids": False},
    }

    media = MediaFileUpload(topic["video_path"], mimetype="video/mp4", resumable=True)
    request = youtube.videos().insert(part=",".join(body.keys()), body=body, media_body=media)
    response = request.execute()
    return f"https://youtube.com/shorts/{response['id']}"


def log_published(topic: dict, result: dict):
    log_file = DATA_DIR / "published_log.json"
    existing = json.loads(log_file.read_text()) if log_file.exists() else []
    existing.append({
        "hash": topic["hash"],
        "title": topic["title"],
        "niche": topic["niche"],
        "published_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "result": result,
    })
    log_file.write_text(json.dumps(existing, indent=2))


def run_publisher(batch_size: int = 3):
    if not QUEUE_FILE.exists():
        return

    queue = json.loads(QUEUE_FILE.read_text())
    ready = [t for t in queue if t.get("status") == "seo_ready"][:batch_size]

    if not ready:
        log.info("No SEO-ready videos to publish.")
        return

    for t in ready:
        log.info(f"Publishing: [{t['niche']}] {t['title'][:50]}")
        try:
            result = post_via_mpt_api(t)
            t["status"] = "published"
            t["publish_result"] = result
            log_published(t, result)
            log.info(f"  Published successfully")
        except Exception as e:
            log.error(f"  Publish failed: {e}")
            try:
                url = post_to_youtube_direct(t)
                t["status"] = "published"
                t["publish_result"] = {"youtube_url": url}
                log.info(f"  Fallback YouTube publish: {url}")
            except Exception as e2:
                log.error(f"  Fallback also failed: {e2}")
                t["status"] = "publish_failed"

        time.sleep(15)

    QUEUE_FILE.write_text(json.dumps(queue, indent=2))


if __name__ == "__main__":
    run_publisher(batch_size=3)
