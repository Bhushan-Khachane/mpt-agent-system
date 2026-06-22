#!/bin/bash
# MPT Agent System - Cron Schedule
# Add these to your crontab: crontab -e

# Trend Scout: runs every 4 hours
0 */4 * * * cd ~/mpt-agent-system && source venv/bin/activate && python orchestrator.py --steps TrendScout >> logs/cron.log 2>&1

# ScriptWriter: runs every 2 hours
30 */2 * * * cd ~/mpt-agent-system && source venv/bin/activate && python orchestrator.py --steps ScriptWriter >> logs/cron.log 2>&1

# Video Production: runs 3x per day
0 8,14,20 * * * cd ~/mpt-agent-system && source venv/bin/activate && python orchestrator.py --steps VideoProducer SEOAgent Publisher >> logs/cron.log 2>&1

# Full pipeline once daily at 7 AM
0 7 * * * cd ~/mpt-agent-system && source venv/bin/activate && python orchestrator.py >> logs/cron.log 2>&1
