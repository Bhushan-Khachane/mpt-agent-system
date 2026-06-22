#!/usr/bin/env python3
"""
VideoProducer Agent

Strategy:
  - Writes a config.toml into the MPT directory with Pexels key + llm_provider=gemini.
  - Calls MPT CLI directly: `python cli.py --video-subject ... --video-script ...`
  - No server, no uv, no HTTP — just subprocess call to cli.py.
  - Output video is found in MPT's storage/tasks/<task_id>/ directory.

DATA_DIR is always resolved relative to this file.
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

REPO_ROOT  = Path(__file__).resolve().parent.parent
DATA_DIR   = REPO_ROOT / "data"
QUEUE_FILE = DATA_DIR / "topics_queue.json"
VIDEO_OUT  = REPO_ROOT / "videos"
VIDEO_OUT.mkdir(parents=True, exist_ok=True)

MPT_DIR = Path(os.getenv("MPT_DIR", "/content/MoneyPrinterTurbo"))

NICHE_VOICES = {
    "ai_tech":       "en-US-GuyNeural",
    "home_cleaning": "en-US-JennyNeural",
    "money_mindset": "en-US-EricNeural",
}


def write_mpt_config():
    """
    Write config.toml into the MPT directory.
    MPT reads Pexels/Gemini keys from this file — NOT from CLI args.
    """
    pexels_key  = os.environ.get("PEXELS_API_KEY", "").strip()
    pixabay_key = os.environ.get("PIXABAY_API_KEY", "").strip()
    gemini_key  = os.environ.get("GEMINI_API_KEY", "").strip()
    gemini_model = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash").strip()

    pexels_entry  = f'["{pexels_key}"]'  if pexels_key  else "[]"
    pixabay_entry = f'["{pixabay_key}"]' if pixabay_key else "[]"

    config_content = f"""\
[app]
video_source = "pexels"
pexels_api_keys = {pexels_entry}
pixabay_api_keys = {pixabay_entry}
llm_provider = "gemini"
subtitle_provider = "edge"
enable_redis = false
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

[ui]
hide_log = false
"""
    config_path = MPT_DIR / "config.toml"
    config_path.write_text(config_content)
    log.info("Wrote MPT config.toml to %s", config_path)


def produce_video(topic: dict) -> Path:
    """
    Call MPT CLI directly. Returns path to output mp4.
    """
    niche        = topic.get("niche", "ai_tech")
    video_terms  = topic.get("video_terms", "AI technology,computer screen")
    voice        = NICHE_VOICES.get(niche, "en-US-GuyNeural")
    task_id      = topic["hash"]

    cli_py = MPT_DIR / "cli.py"
    if not cli_py.exists():
        raise FileNotFoundError(
            f"MPT cli.py not found at {cli_py}\n"
            "Make sure MoneyPrinterTurbo is cloned to /content/MoneyPrinterTurbo"
        )

    cmd = [
        sys.executable, str(cli_py),
        "--video-subject",  topic["video_subject"],
        "--video-script",   topic["script"],
        "--video-terms",    video_terms,
        "--video-count",    "1",
        "--video-source",   "pexels",
        "--video-aspect",   "9:16",
        "--voice-name",     voice,
        "--task-id",        task_id,
    ]

    log.info("Running MPT CLI for: %s", topic["title"][:60])
    result = subprocess.run(
        cmd,
        cwd=str(MPT_DIR),
        capture_output=True,
        text=True,
        timeout=600,  # 10 min max per video
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"MPT CLI failed (exit {result.returncode}):\n"
            f"STDOUT: {result.stdout[-800:]}\n"
            f"STDERR: {result.stderr[-800:]}"
        )

    # MPT saves output to storage/tasks/<task_id>/
    task_dir = MPT_DIR / "storage" / "tasks" / task_id
    mp4_files = sorted(task_dir.glob("*.mp4")) if task_dir.exists() else []
    if not mp4_files:
        # Fall back: search recursively
        mp4_files = sorted((MPT_DIR / "storage").rglob(f"*{task_id}*.mp4"))

    if not mp4_files:
        raise FileNotFoundError(
            f"MPT ran successfully but no .mp4 found in {task_dir}\n"
            f"MPT stdout: {result.stdout[-400:]}"
        )

    src = mp4_files[-1]  # take last (final) file
    dst = VIDEO_OUT / f"{niche}_{task_id}.mp4"
    shutil.copy2(src, dst)
    log.info("  Video copied to %s", dst)
    return dst


def run_video_producer(batch_size: int = 3):
    if not QUEUE_FILE.exists():
        log.warning("Queue file not found: %s", QUEUE_FILE)
        return

    # Write/refresh MPT config before every run
    write_mpt_config()

    queue    = json.loads(QUEUE_FILE.read_text())
    scripted = [t for t in queue if t.get("status") == "scripted"][:batch_size]

    if not scripted:
        log.info("No scripted topics ready for video production.")
        return

    for t in scripted:
        log.info("Producing: [%s] %s", t["niche"], t["title"][:60])
        try:
            video_path    = produce_video(t)
            t["video_path"] = str(video_path)
            t["status"]     = "video_ready"
        except Exception as exc:
            log.error("  Production failed: %s", exc)
            t["status"] = "production_failed"
            t["error"]  = str(exc)

    QUEUE_FILE.write_text(json.dumps(queue, indent=2))
    done = sum(1 for t in scripted if t.get("status") == "video_ready")
    log.info("VideoProducer done: %d/%d videos ready.", done, len(scripted))


if __name__ == "__main__":
    run_video_producer(batch_size=3)
