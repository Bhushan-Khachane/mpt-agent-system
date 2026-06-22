#!/bin/bash
set -e

echo "=== MPT Agent System Setup ==="

# Project structure
mkdir -p agents data videos logs credentials

# Virtual env
python3.11 -m venv venv
source venv/bin/activate

# Install deps
pip install -q feedparser pytrends requests google-api-python-client google-auth-httplib2 google-auth-oauthlib

# Init empty queue
echo "[]" > data/topics_queue.json
echo "{}" > data/seen_topics.json

# Touch agent __init__
touch agents/__init__.py

echo ""
echo "Setup complete. Now:"
echo "  1. cp .env.example .env  and fill in your keys"
echo "  2. python orchestrator.py --dry-run   (test the pipeline)"
echo "  3. python orchestrator.py --steps TrendScout  (real first run)"
