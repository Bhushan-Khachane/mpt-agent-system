# 🤖 MPT Agent System

> Fully automated AI agent pipeline for [MoneyPrinterTurbo](https://github.com/harry0703/MoneyPrinterTurbo) — researches trending topics, writes scripts, produces stock-footage videos, generates SEO metadata, and cross-posts to YouTube Shorts, Instagram Reels & Facebook Reels across **3 monetisable niches**.

## 🎯 Niches Covered

| Niche | Sources | Voice | Strategy |
|-------|---------|-------|----------|
| **AI & Tech** | TechCrunch, Verge, HuggingFace, r/artificial | GuyNeural | High CPM + SaaS sponsorships |
| **Home Cleaning / Satisfying** | GoodHousekeeping, r/CleaningTips, Apartment Therapy | JennyNeural | Scale & volume, brand deals |
| **Money Mindset / Side Hustle** | Investopedia, NYT Business, r/personalfinance | EricNeural | Finance CPM + affiliate income |

## 🏗️ Architecture

```
[TrendScout] → [ScriptWriter] → [VideoProducer] → [SEOAgent] → [Publisher]
     ↓               ↓                ↓               ↓             ↓
  RSS/Reddit      Ollama LLM       MPT CLI/API     Ollama LLM   YouTube +
  PyTrends        per-niche        stock footage   metadata     Instagram +
  → queue          → script        → .mp4          → tags/desc  Facebook Reels
```

All agents share `data/topics_queue.json` as a state store. Topics progress through statuses:
`pending → scripted → video_ready → seo_ready → published`

## 🚀 Quick Start

```bash
# 1. Clone
git clone https://github.com/Bhushan-Khachane/mpt-agent-system
cd mpt-agent-system

# 2. Setup
bash setup.sh

# 3. Configure
cp .env.example .env
# Edit .env with your Pexels key, MPT path, channel IDs

# 4. Test
python orchestrator.py --dry-run

# 5. First run
python orchestrator.py --steps TrendScout
python orchestrator.py --steps ScriptWriter VideoProducer
```

## 📅 Cron Schedule

```
Every 4 hrs   → TrendScout (fetch new topics)
Every 2 hrs   → ScriptWriter (generate scripts)
8AM/2PM/8PM   → VideoProducer + SEOAgent + Publisher
Daily 7AM     → Full pipeline
```

Add to crontab with: `crontab -e` then paste from `crontab.sh`

## 📁 Project Structure

```
mpt-agent-system/
├── agents/
│   ├── trend_scout.py      # RSS + Reddit + PyTrends scraper
│   ├── script_writer.py    # Ollama LLM script generator
│   ├── video_producer.py   # MPT CLI/API wrapper
│   ├── seo_agent.py        # Title/tags/description generator
│   └── publisher.py        # Cross-platform uploader
├── orchestrator.py         # Master pipeline runner
├── setup.sh                # One-time environment setup
├── crontab.sh              # Cron schedule reference
├── .env.example            # Environment variables template
└── data/                   # Runtime state (gitignored)
```

## ⚙️ Prerequisites

- Python 3.11+
- [MoneyPrinterTurbo](https://github.com/harry0703/MoneyPrinterTurbo) installed locally
- [Ollama](https://ollama.ai) running locally with `gemma3:4b` pulled
- Pexels API key (free)
- YouTube OAuth credentials per channel
- (Optional) Upload-Post.com account for cross-platform posting

## 📊 Expected Output

~9 videos/day across 3 niches (3 per niche), posted to YouTube Shorts + Instagram Reels + Facebook Reels automatically.

## 📝 License

MIT
