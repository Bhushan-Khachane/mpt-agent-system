#!/usr/bin/env python3
"""
VideoProducer Agent

Calls MPT CLI (cli.py) directly via subprocess.
Writes a config.toml whose structure matches MPT's config.example.toml exactly:
  - [app] section: pexels/pixabay/coverr keys, llm_provider, subtitle_provider, redis, concurrency
  - Root-level LLM keys (gemini_api_key, gemini_model_name etc.) AFTER [app] block
  - [whisper], [proxy], [azure], [siliconflow], [ui] sections

DATA_DIR and MPT_DIR are both resolved lazily (inside functions) so they always
reflect env vars set AFTER the module is imported.
"""
import json
import logging
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [VideoProducer] %(message)s")
log = logging.getLogger(__name__)

# Repo root is always relative to THIS file — never CWD
REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR  = REPO_ROOT / "data"
VIDEO_OUT = REPO_ROOT / "videos"
QUEUE_FILE = DATA_DIR / "topics_queue.json"

# Use Edge TTS voices from MoneyPrinterTurbo's built-in Azure V1 path.
# This avoids Gemini TTS errors and keeps TTS entirely inside MPT.
NICHE_VOICES = {
    "ai_tech":       "en-US-GuyNeural",
    "home_cleaning": "en-US-JennyNeural",
    "money_mindset": "en-US-EricNeural",
}


def _mpt_dir() -> Path:
    """Resolve MPT_DIR lazily so it picks up env var set after import."""
    return Path(os.environ.get("MPT_DIR", "/content/MoneyPrinterTurbo"))


def write_mpt_config():
    """
    Write config.toml that exactly matches MPT's config.example.toml structure:
      [app]          — pexels/pixabay/coverr keys, llm_provider, subtitle_provider etc.
      gemini_api_key — root-level (outside [app]) like in example.toml
      [whisper]      — model size and device
      [proxy]        — empty
      [azure]        — empty (we use Edge TTS, not Azure Speech)
      [siliconflow]  — empty
      [ui]           — upload-post disabled
    """
    mpt = _mpt_dir()
    pexels_key   = os.environ.get("PEXELS_API_KEY",  "").strip()
    pixabay_key  = os.environ.get("PIXABAY_API_KEY", "").strip()
    coverr_key   = os.environ.get("COVERR_API_KEY",  "").strip()
    gemini_key   = os.environ.get("GEMINI_API_KEY",  "").strip()
    gemini_model = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash").strip()

    # TOML array syntax for API key lists
    pexels_entry  = f'["{pexels_key}"]'  if pexels_key  else "[]"
    pixabay_entry = f'["{pixabay_key}"]' if pixabay_key else "[]"
    coverr_entry  = f'["{coverr_key}"]'  if coverr_key  else "[]"

    config = f"""[app]
video_source = "pexels"
pexels_api_keys = {pexels_entry}
pixabay_api_keys = {pixabay_entry}
coverr_api_keys = {coverr_entry}
llm_provider = "gemini"
subtitle_provider = "edge"
material_directory = ""
edge_tts_timeout = 30
tls_verify = true
enable_redis = false
redis_host = "localhost"
redis_port = 6379
redis_db = 0
redis_password = ""
max_concurrent_tasks = 3
max_queued_tasks = 50

gemini_api_key = "{gemini_key}"
gemini_model_name = "{gemini_model}"

[whisper]
model_size = "tiny"
device = "cpu"
compute_type = "int8"

[proxy]

[azure]
speech_key = ""
speech_region = ""

[siliconflow]
api_key = ""

[ui]
hide_log = false
upload_post_enabled = false
upload_post_api_key = ""
upload_post_username = ""
upload_post_platforms = ["tiktok", "instagram"]
upload_post_auto_upload = false
upload_post_youtube_privacy_status = "public"
"""
    config_path = mpt / "config.toml"
    config_path.write_text(config, encoding="utf-8")
    log.info("Wrote config.toml to %s", config_path)
    log.info("  llm_provider=gemini  model=%s  pexels=%s", gemini_model, "set" if pexels_key else "MISSING")


def produce_video(topic: dict) -> Path:
    """Run MPT CLI for one topic.

    We let MoneyPrinterTurbo handle the full pipeline. We only pass:
      - video_subject: topic title
      - video_script : full narration from ScriptWriter
      - video_terms  : comma-separated search keywords (optional)
      - voice_name   : Edge TTS voice (per-niche)
      - task_id      : used to locate outputs
    """
    mpt         = _mpt_dir()
    niche       = topic.get("niche", "ai_tech")
    video_terms = (topic.get("video_terms") or "").strip()
    voice       = NICHE_VOICES.get(niche, "en-US-GuyNeural")
    task_id     = topic["hash"]

    cli_py = mpt / "cli.py"
    if not cli_py.exists():
        raise FileNotFoundError(
            f"MPT cli.py not found: {cli_py}\n"
            "Ensure MoneyPrinterTurbo is cloned to /content/MoneyPrinterTurbo"
        )

    # Escape double-quotes and newlines in script/subject to avoid shell issues
    subject = topic["video_subject"].replace('"', "'")
    script  = topic["script"].replace('"', "'").replace("\n", " ")

    cmd = [
        sys.executable,
        str(cli_py),
        "--video-subject", subject,
        "--video-script",  script,
        "--voice-name",    voice,
        "--task-id",       task_id,
    ]
    if video_terms:
        cmd.extend(["--video-terms", video_terms])

    log.info("Running MPT CLI | task=%s | niche=%s", task_id, niche)
    log.info("  Subject: %s", subject[:80])
    log.info("  Voice  : %s", voice)
    if video_terms:
        log.info("  Terms  : %s", video_terms[:80])

    result = subprocess.run(
        cmd,
        cwd=str(mpt),
        capture_output=True,
        text=True,
        timeout=900,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"MPT CLI failed (exit {result.returncode})\n"
            f"STDOUT (last 1000): {result.stdout[-1000:]}\n"
            f"STDERR (last 1000): {result.stderr[-1000:]}"
        )

    log.info("MPT CLI stdout: %s", result.stdout[-400:])

    # MPT saves output to storage/tasks/<task_id>/final-*.mp4
    task_dir  = mpt / "storage" / "tasks" / task_id
    mp4_files = sorted(task_dir.glob("final-*.mp4")) if task_dir.exists() else []
    if not mp4_files:
        mp4_files = sorted(task_dir.glob("*.mp4")) if task_dir.exists() else []
    if not mp4_files:
        mp4_files = sorted((mpt / "storage").rglob(f"*{task_id}*.mp4"))

    if not mp4_files:
        raise FileNotFoundError(
            f"MPT succeeded but no .mp4 found.\n"
            f"Expected: {task_dir}/final-*.mp4\n"
            f"stdout: {result.stdout[-400:]}"
        )

    VIDEO_OUT.mkdir(parents=True, exist_ok=True)
    src = mp4_files[-1]
    dst = VIDEO_OUT / f"{niche}_{task_id}.mp4"
    shutil.copy2(src, dst)
    log.info("Video saved: %s", dst)
    return dst


def run_video_producer(batch_size: int = 2):
    if not QUEUE_FILE.exists():
        log.warning("Queue file not found: %s", QUEUE_FILE)
        return

    # Refresh config.toml before every run (picks up current env vars)
    write_mpt_config()

    queue    = json.loads(QUEUE_FILE.read_text())
    scripted = [t for t in queue if t.get("status") == "scripted"][:batch_size]

    if not scripted:
        log.info("No scripted topics ready. Run ScriptWriter first.")
        return

    for t in scripted:
        log.info("Producing: [%s] %s", t["niche"], t["title"][:60])
        try:
            video_path      = produce_video(t)
            t["video_path"] = str(video_path)
            t["status"]     = "video_ready"
            log.info("  ✅ Done: %s", video_path.name)
        except Exception as exc:
            log.error("  ❌ Failed: %s", exc)
            t["status"] = "production_failed"
            t["error"]  = str(exc)[:500]
        time.sleep(2)

    QUEUE_FILE.write_text(json.dumps(queue, indent=2))
    done = sum(1 for t in scripted if t.get("status") == "video_ready")
    log.info("VideoProducer done: %d/%d videos ready.", done, len(scripted))


if __name__ == "__main__":
    run_video_producer(batch_size=1)
