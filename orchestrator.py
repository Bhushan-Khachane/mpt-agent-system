#!/usr/bin/env python3
"""
Master Orchestrator
Runs the full pipeline: TrendScout → ScriptWriter → VideoProducer → SEOAgent → Publisher
Can be run manually or via cron / n8n webhook.
"""
import argparse, logging, sys, os
from datetime import datetime
from pathlib import Path

Path("logs").mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [Orchestrator] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/orchestrator.log"),
    ],
)
log = logging.getLogger(__name__)

from agents.trend_scout import run_trend_scout
from agents.script_writer import run_script_writer
from agents.video_producer import run_video_producer
from agents.seo_agent import run_seo_agent
from agents.publisher import run_publisher


PIPELINE_STEPS = [
    ("TrendScout",    lambda: run_trend_scout()),
    ("ScriptWriter",  lambda: run_script_writer(batch_size=6)),
    ("VideoProducer", lambda: run_video_producer(batch_size=3)),
    ("SEOAgent",      lambda: run_seo_agent(batch_size=6)),
    ("Publisher",     lambda: run_publisher(batch_size=3)),
]


def run_pipeline(steps: list = None, dry_run: bool = False):
    selected = [(n, fn) for n, fn in PIPELINE_STEPS if steps is None or n in steps]
    log.info(f"=== Pipeline START | {datetime.utcnow().isoformat()} ===")
    log.info(f"Running steps: {[n for n,_ in selected]}")

    for name, fn in selected:
        log.info(f"--- Step: {name} ---")
        if dry_run:
            log.info(f"  [DRY RUN] Skipping {name}")
            continue
        try:
            fn()
            log.info(f"  {name} complete")
        except Exception as e:
            log.error(f"  {name} FAILED: {e}")

    log.info(f"=== Pipeline END | {datetime.utcnow().isoformat()} ===")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MPT Agent Orchestrator")
    parser.add_argument("--steps", nargs="+", help="Run specific steps only",
                        choices=[n for n,_ in PIPELINE_STEPS])
    parser.add_argument("--dry-run", action="store_true", help="Log only, no execution")
    args = parser.parse_args()
    run_pipeline(steps=args.steps, dry_run=args.dry_run)
