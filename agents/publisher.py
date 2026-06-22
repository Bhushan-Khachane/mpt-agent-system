#!/usr/bin/env python3
"""
Publisher Agent

Strategy:
  1. Try YouTube Data API v3 direct upload (needs token file).
  2. If no token, log the video path + SEO metadata so you can upload manually.

NOTE: MPT is a video GENERATOR, not a social media poster.
The upload-post.com integration is available inside MPT's WebUI config
but is not exposed via CLI. We use YouTube API directly here.

All os.getenv calls are LAZY (inside run_publisher) so they pick up env vars
set in the Colab Step 2 cell.
"""
import json
import logging
import os
import time
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [Publisher] %(message)s")
log = logging.getLogger(__name__)

REPO_ROOT  = Path(__file__).resolve().parent.parent
DATA_DIR   = REPO_ROOT / "data"
QUEUE_FILE = DATA_DIR / "topics_queue.json"
CREDS_DIR  = REPO_ROOT / "credentials"


def _get_channel_map() -> dict:
    """Read channel IDs lazily so they pick up env vars set after import."""
    return {
        "ai_tech": {
            "youtube":   os.environ.get("YT_CHANNEL_AI", ""),
            "instagram": os.environ.get("IG_ACCOUNT_AI", ""),
        },
        "home_cleaning": {
            "youtube":   os.environ.get("YT_CHANNEL_CLEAN", ""),
            "instagram": os.environ.get("IG_ACCOUNT_CLEAN", ""),
        },
        "money_mindset": {
            "youtube":   os.environ.get("YT_CHANNEL_MONEY", ""),
            "instagram": os.environ.get("IG_ACCOUNT_MONEY", ""),
        },
    }


def _upload_to_youtube(topic: dict) -> str:
    """Upload to YouTube using OAuth token file."""
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from google.oauth2.credentials import Credentials

    niche      = topic["niche"]
    seo        = topic.get("seo", {})
    token_file = CREDS_DIR / f"youtube_{niche}_token.json"

    if not token_file.exists():
        raise FileNotFoundError(
            f"YouTube OAuth token missing: {token_file}\n"
            "Upload it to the credentials/ folder then re-run Step 7."
        )

    creds   = Credentials.from_authorized_user_file(str(token_file))
    youtube = build("youtube", "v3", credentials=creds)

    body = {
        "snippet": {
            "title":       seo.get("youtube_title", topic["title"])[:100],
            "description": seo.get("youtube_description", "")[:5000],
            "tags":        seo.get("youtube_tags", [])[:500],
            "categoryId":  "28",
        },
        "status": {"privacyStatus": "public", "madeForKids": False},
    }
    media   = MediaFileUpload(topic["video_path"], mimetype="video/mp4", resumable=True)
    request = youtube.videos().insert(
        part=",".join(body.keys()), body=body, media_body=media
    )
    response = request.execute()
    return f"https://youtube.com/shorts/{response['id']}"


def _log_for_manual_upload(topic: dict):
    """Save a JSON summary so you can manually upload later."""
    seo        = topic.get("seo", {})
    manual_log = DATA_DIR / "manual_upload_queue.json"
    existing   = json.loads(manual_log.read_text()) if manual_log.exists() else []
    existing.append({
        "hash":               topic["hash"],
        "niche":              topic["niche"],
        "title":              topic["title"],
        "video_path":         topic.get("video_path", ""),
        "youtube_title":      seo.get("youtube_title", topic["title"]),
        "youtube_description":seo.get("youtube_description", ""),
        "youtube_tags":       seo.get("youtube_tags", []),
        "instagram_caption":  seo.get("instagram_caption", ""),
        "queued_at":          time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    })
    manual_log.write_text(json.dumps(existing, indent=2))
    log.info("  Saved to manual_upload_queue.json for manual upload.")


def _log_published(topic: dict, result: dict):
    log_file = DATA_DIR / "published_log.json"
    existing = json.loads(log_file.read_text()) if log_file.exists() else []
    existing.append({
        "hash":         topic["hash"],
        "title":        topic["title"],
        "niche":        topic["niche"],
        "published_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "result":       result,
    })
    log_file.write_text(json.dumps(existing, indent=2))


def run_publisher(batch_size: int = 3):
    if not QUEUE_FILE.exists():
        log.warning("Queue file not found: %s", QUEUE_FILE)
        return

    queue = json.loads(QUEUE_FILE.read_text())
    ready = [t for t in queue if t.get("status") == "seo_ready"][:batch_size]

    if not ready:
        log.info("No SEO-ready videos to publish.")
        return

    CREDS_DIR.mkdir(parents=True, exist_ok=True)

    for t in ready:
        log.info("Publishing: [%s] %s", t["niche"], t["title"][:50])
        try:
            url    = _upload_to_youtube(t)
            t["status"]         = "published"
            t["publish_result"] = {"youtube_url": url}
            _log_published(t, {"youtube_url": url})
            log.info("  Published: %s", url)
        except FileNotFoundError as fnf:
            log.warning("  No token — queuing for manual upload. (%s)", fnf)
            t["status"] = "pending_manual_upload"
            _log_for_manual_upload(t)
        except Exception as exc:
            log.error("  Publish failed: %s", exc)
            t["status"] = "publish_failed"
            t["error"]  = str(exc)

        time.sleep(5)

    QUEUE_FILE.write_text(json.dumps(queue, indent=2))


if __name__ == "__main__":
    run_publisher(batch_size=3)
