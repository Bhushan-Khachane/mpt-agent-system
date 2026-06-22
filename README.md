# 🤖 MPT Agent System

> Fully automated AI agent pipeline for [MoneyPrinterTurbo](https://github.com/harry0703/MoneyPrinterTurbo) — researches trending topics, writes scripts with **Gemini API**, produces stock-footage videos, generates SEO metadata, and cross-posts to YouTube Shorts, Instagram Reels & Facebook Reels across **3 monetisable niches**.

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Bhushan-Khachane/mpt-agent-system/blob/main/colab_runner.ipynb)

---

## 🎯 Niches Covered

| Niche | Sources | Voice | Strategy |
|-------|---------|-------|----------|
| **AI & Tech** | TechCrunch, The Verge, r/artificial | GuyNeural | High CPM + SaaS sponsorships |
| **Home Cleaning** | GoodHousekeeping, r/CleaningTips | JennyNeural | Scale & volume, brand deals |
| **Money Mindset** | Investopedia, r/personalfinance | EricNeural | Finance CPM + affiliate income |

---

## 🏗️ Architecture

```
[TrendScout] → [ScriptWriter] → [VideoProducer] → [SEOAgent] → [Publisher]
     ↓               ↓                ↓               ↓             ↓
  RSS/Reddit      Gemini API       MPT CLI/API     Gemini API   YouTube +
  PyTrends         (scripts)        stock footage   (metadata)   Instagram +
  → queue.json                      → .mp4                      Facebook Reels
```

---

## 🧠 LLM — Gemini API only

| Env var | Default | Notes |
|---------|---------|-------|
| `GEMINI_API_KEY` | **required** | Free at [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey) |
| `GEMINI_MODEL` | `gemini-2.0-flash` | Switch to `gemini-2.5-flash-preview` for longer outputs |

No local model loading. No GPU required. Works on any CPU machine or free Colab runtime.

---

## 🚀 Quick Start (Google Colab — CPU)

1. Click **Open in Colab** badge above
2. Set `GEMINI_API_KEY` in Step 2 cell (free key at [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey))
3. Run all cells — done

---

## 🚀 Quick Start (Local / Mac M4)

```bash
git clone https://github.com/Bhushan-Khachane/mpt-agent-system
cd mpt-agent-system
bash setup.sh
cp .env.example .env
# Edit .env — set GEMINI_API_KEY, MPT_DIR, PEXELS_API_KEY, channel IDs
python orchestrator.py --dry-run
python orchestrator.py
```

---

## 📅 Cron Schedule

```
Every 4 hrs   → TrendScout
Every 2 hrs   → ScriptWriter
8AM/2PM/8PM   → VideoProducer + SEOAgent + Publisher
```

Paste from `crontab.sh` into `crontab -e`.

---

## 📁 Project Structure

```
mpt-agent-system/
├── agents/
│   ├── llm_client.py       ← Gemini API wrapper (only LLM dependency)
│   ├── trend_scout.py      ← RSS + Reddit + PyTrends scraper
│   ├── script_writer.py    ← Gemini script generator
│   ├── video_producer.py   ← MPT CLI/API wrapper
│   ├── seo_agent.py        ← Gemini title/tags/description generator
│   └── publisher.py        ← cross-platform uploader
├── orchestrator.py
├── colab_runner.ipynb      ← Colab notebook (CPU, no GPU)
├── setup.sh
├── crontab.sh
└── .env.example
```

---

## ⚙️ Prerequisites

- Python 3.11+
- [MoneyPrinterTurbo](https://github.com/harry0703/MoneyPrinterTurbo)
- **Gemini API key** — free at [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
- Pexels API key — free at [pexels.com/api](https://www.pexels.com/api/)
- YouTube OAuth credentials per channel

---

## 📝 License

MIT
