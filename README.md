# Claw Control Room

A lightweight GitHub Pages dashboard that shows what Claw is doing throughout the day:
- current focus
- active block
- today timeline
- next scheduled jobs
- recent findings/wins

## Local build

```bash
python3 scripts/build_status_json.py
open index.html
```

## Update + publish

```bash
./scripts/update_and_push.sh
```

## Suggested automation

Run `scripts/update_and_push.sh` every 30 minutes from OpenClaw cron or launchd.

## Data source

Reads from:
- `~/.openclaw/workspace/DAILY_PLAN.md`
- `~/.openclaw/workspace/TODAY_STATUS.md`
- `~/.openclaw/workspace/memory/YYYY-MM-DD.md`
- `~/.openclaw/cron/jobs.json`
- `~/.openclaw/workspace/scripts/reliability_watchdog_report.py`
