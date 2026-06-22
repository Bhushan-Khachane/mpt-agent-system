# 🤖 MPT Agent System

> Fully automated AI agent pipeline for [MoneyPrinterTurbo](https://github.com/harry0703/MoneyPrinterTurbo) — researches trending topics, writes scripts with **Gemma 3 4B**, produces stock-footage videos, generates SEO metadata, and cross-posts to YouTube Shorts, Instagram Reels & Facebook Reels across **3 monetisable niches**.

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Bhushan-Khachane/mpt-agent-system/blob/main/colab_runner.ipynb)

---

## 🎯 Niches Covered

| Niche | Sources | Voice | Strategy |
|-------|---------|-------|----------|
| **AI & Tech** | TechCrunch, Verge, HuggingFace, r/artificial | GuyNeural | High CPM + SaaS sponsorships |
| **Home Cleaning / Satisfying** | GoodHousekeeping, r/CleaningTips, Apartment Therapy | JennyNeural | Scale & volume, brand deals |
| **Money Mindset / Side Hustle** | Investopedia, NYT Business, r/personalfinance | EricNeural | Finance CPM + affiliate income |

---

## 🏗️ Architecture

```
[TrendScout] → [ScriptWriter] → [VideoProducer] → [SEOAgent] → [Publisher]
     ↓               ↓                ↓               ↓             ↓
  RSS/Reddit      Gemma 3 4B       MPT CLI/API     Gemma 3 4B   YouTube +
  PyTrends        (HF/Ollama/      stock footage   metadata     Instagram +
  → queue.json     Gemini)         → .mp4          → tags/desc  Facebook Reels
```

All agents share `data/topics_queue.json` as a state store.  
Topics progress: `pending → scripted → video_ready → seo_ready → published`

---

## 🧠 LLM Backend — Auto-detected

| Backend | When used | How to force |
|---------|-----------|---------------|
| `hf_gemma` | Colab GPU / CUDA available | `LLM_BACKEND=hf_gemma` |
| `ollama` | Local Ollama server reachable | `LLM_BACKEND=ollama` |
| `gemini` | `GEMINI_API_KEY` set | `LLM_BACKEND=gemini` |

Model: `google/gemma-3-4b-it` (4-bit quantised, fits T4 free tier)

---

## 🚀 Quick Start (Google Colab)

1. Click **Open in Colab** badge above
2. Set Runtime → **T4 GPU**
3. Fill in your keys in Step 2 cell
4. Run all cells top to bottom

---

## 🚀 Quick Start (Local / Mac)

```bash
git clone https://github.com/Bhushan-Khachane/mpt-agent-system
cd mpt-agent-system
bash setup.sh
cp .env.example .env
# Edit .env — set MPT_DIR, PEXELS_API_KEY, channel IDs
python orchestrator.py --dry-run
python orchestrator.py --steps TrendScout
python orchestrator.py
```

---

## 📅 Cron Schedule (local)

```
Every 4 hrs   → TrendScout (fetch new topics)
Every 2 hrs   → ScriptWriter
8AM/2PM/8PM   → VideoProducer + SEOAgent + Publisher
Daily 7AM     → Full pipeline
```

Add to crontab: `crontab -e` then paste from `crontab.sh`

---

## 📁 Project Structure

```
mpt-agent-system/
├── agents/
│   ├── llm_client.py       ← unified Gemma/Ollama/Gemini interface
│   ├── trend_scout.py      ← RSS + Reddit + PyTrends scraper
│   ├── script_writer.py    ← LLM script generator
│   ├── video_producer.py   ← MPT CLI/API wrapper
│   ├── seo_agent.py        ← title/tags/description generator
│   └── publisher.py        ← cross-platform uploader
├── orchestrator.py         ← master pipeline runner
├── colab_runner.ipynb      ← Google Colab notebook
├── setup.sh
├── crontab.sh
└── .env.example
```

---

## ⚙️ Prerequisites

- Python 3.11+
- [MoneyPrinterTurbo](https://github.com/harry0703/MoneyPrinterTurbo) installed (local or Colab)
- Pexels API key (free at pexels.com/api)
- YouTube OAuth credentials per channel
- (Optional) HuggingFace token for gated models
- (Optional) Upload-Post.com account for cross-platform posting

---

## 📊 Expected Output

~9 videos/day across 3 niches (3 per niche), posted to YouTube Shorts + Instagram Reels + Facebook Reels automatically.

## 📝 License

MIT
