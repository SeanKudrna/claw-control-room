# Claw Control Room

A GitHub Pages dashboard that gives a readable window into Claw's day:
- current focus
- active work block
- timeline of planned tasks
- next scheduled jobs
- recent findings/wins

## Repository standards

This repo follows a strict quality contract in `AGENTS.md`:
- modular code first
- documented changes always
- test/compile gates before publish

Read next:
- `docs/ARCHITECTURE.md`
- `docs/DEVELOPMENT.md`
- `CHANGELOG.md`

## Local build

```bash
python3 scripts/build_status_json.py
open index.html
```

## Update + publish

```bash
./scripts/update_and_push.sh
```

## Data sources

Builder reads from:
- `~/.openclaw/workspace/DAILY_PLAN.md`
- `~/.openclaw/workspace/TODAY_STATUS.md`
- `~/.openclaw/workspace/memory/YYYY-MM-DD.md`
- `~/.openclaw/cron/jobs.json`
- `~/.openclaw/workspace/scripts/reliability_watchdog_report.py`

## Suggested automation

Run `scripts/update_and_push.sh` from OpenClaw cron (already configured) for continuous dashboard refresh.
