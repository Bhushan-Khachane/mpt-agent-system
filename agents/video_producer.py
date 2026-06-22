#!/usr/bin/env python3
"""
VideoProducer Agent
On Colab: always uses MPT HTTP API (MPT_USE_API=true).
On local Mac: can use CLI mode.
"""
import json, logging, os, subprocess, time
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [VideoProducer] %(message)s")
log = logging.getLogger(__name__)

DATA_DIR   = Path("data")
QUEUE_FILE = DATA_DIR / "topics_queue.json"
VIDEO_OUT  = Path("videos")
VIDEO_OUT.mkdir(exist_ok=True)

MPT_DIR     = Path(os.getenv("MPT_DIR", os.path.expanduser("~/MoneyPrinterTurbo")))
MPT_API_URL = os.getenv("MPT_API_URL", "http://localhost:8080")

NICHE_VOICES = {
    "ai_tech":       "en-US-GuyNeural",
    "home_cleaning": "en-US-JennyNeural",
    "money_mindset": "en-US-EricNeural",
}


def start_mpt_server():
    """Start MPT FastAPI server in background if not already running."""
    import requests
    try:
        r = requests.get(f"{MPT_API_URL}/ping", timeout=3)
        if r.status_code == 200:
            log.info("MPT API server already running.")
            return
    except Exception:
        pass

    log.info("Starting MPT API server in background...")
    main_py = MPT_DIR / "main.py"
    if not main_py.exists():
        raise FileNotFoundError(
            f"MPT main.py not found at {main_py}. "
            "Make sure MoneyPrinterTurbo is cloned to /content/MoneyPrinterTurbo"
        )
    proc = subprocess.Popen(
        ["python", str(main_py), "--port", "8080"],
        cwd=str(MPT_DIR),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    # Wait up to 30s for server to be ready
    for i in range(30):
        time.sleep(1)
        try:
            r = requests.get(f"{MPT_API_URL}/ping", timeout=2)
            if r.status_code == 200:
                log.info(f"MPT API server ready (PID {proc.pid})")
                return
        except Exception:
            pass
    raise TimeoutError("MPT API server did not start within 30 seconds.")


def produce_via_api(topic: dict) -> Path:
    import requests as req
    niche   = topic.get("niche", "ai_tech")
    payload = {
        "video_subject":  topic["video_subject"],
        "video_script":   topic["script"],
        "video_terms":    " ".join(topic.get("search_terms", [])[:4]),
        "video_aspect":   "portrait",
        "voice_name":     NICHE_VOICES.get(niche, "en-US-GuyNeural"),
        "video_source":   "pexels",
        "video_count":    1,
        "pexels_api_key": os.getenv("PEXELS_API_KEY", ""),
    }
    r = req.post(f"{MPT_API_URL}/api/v1/videos", json=payload, timeout=60)
    r.raise_for_status()
    task_id = r.json()["task_id"]
    log.info(f"  MPT task created: {task_id}")

    for _ in range(60):
        time.sleep(5)
        status_r = req.get(f"{MPT_API_URL}/api/v1/videos/{task_id}")
        data = status_r.json()
        if data.get("status") == "completed":
            video_url = data["videos"][0]
            out_path  = VIDEO_OUT / f"{niche}_{topic['hash']}.mp4"
            video_data = req.get(f"{MPT_API_URL}{video_url}").content
            out_path.write_bytes(video_data)
            return out_path
        elif data.get("status") == "failed":
            raise RuntimeError(f"MPT task failed: {data}")
        log.info(f"  Task status: {data.get('status', 'unknown')}")

    raise TimeoutError("MPT API timed out after 5 minutes.")


def produce_via_cli(topic: dict) -> Path:
    """CLI mode — for local Mac with uv installed."""
    niche    = topic.get("niche", "ai_tech")
    out_path = VIDEO_OUT / f"{niche}_{topic['hash']}.mp4"
    main_py  = MPT_DIR / "main.py"

    if not main_py.exists():
        raise FileNotFoundError(f"MPT main.py not found at {main_py}")

    cmd = [
        "python", str(main_py),
        "--video-subject", topic["video_subject"],
        "--video-script",  topic["script"],
        "--video-count",   "1",
        "--video-source",  "pexels",
        "--video-aspect",  "portrait",
        "--voice-name",    NICHE_VOICES.get(niche, "en-US-GuyNeural"),
        "--output",        str(out_path),
    ]
    log.info(f"Running MPT CLI: {topic['title'][:50]}")
    result = subprocess.run(cmd, cwd=str(MPT_DIR), capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        raise RuntimeError(f"MPT CLI failed:\n{result.stderr[-500:]}")
    found = list(VIDEO_OUT.glob(f"*{topic['hash']}*"))
    return found[0] if found else out_path


def run_video_producer(batch_size: int = 3, use_api: bool = True):
    if not QUEUE_FILE.exists():
        log.warning("No topics queue found.")
        return

    queue    = json.loads(QUEUE_FILE.read_text())
    scripted = [t for t in queue if t.get("status") == "scripted"][:batch_size]

    if not scripted:
        log.info("No scripted topics ready for video production.")
        return

    if use_api:
        start_mpt_server()

    for t in scripted:
        log.info(f"Producing video: {t['title'][:60]}")
        try:
            video_path = produce_via_api(t) if use_api else produce_via_cli(t)
            t["video_path"] = str(video_path)
            t["status"]     = "video_ready"
            log.info(f"  Video saved: {video_path}")
        except Exception as e:
            log.error(f"  Production failed: {e}")
            t["status"] = "production_failed"
            t["error"]  = str(e)

    QUEUE_FILE.write_text(json.dumps(queue, indent=2))


if __name__ == "__main__":
    use_api = os.getenv("MPT_USE_API", "true").lower() == "true"
    run_video_producer(batch_size=3, use_api=use_api)
