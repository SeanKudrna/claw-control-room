# Architecture

## Purpose
Claw Control Room is a static dashboard that exposes a readable, near-real-time view of Claw's work state:
- current focus
- active work
- timeline blocks
- next jobs
- recent findings

## Runtime model

1) Data generation (Python)
- `scripts/build_status_json.py` is the CLI entrypoint.
- It delegates to `scripts/lib/status_builder.py` for all parsing and payload assembly.
- Output is written to `data/status.json`.

2) Static rendering (browser)
- `app.js` fetches `data/status.json`.
- `index.html` and `styles.css` render cards/tables/timeline.

3) Publish flow (GitHub Pages)
- `scripts/update_and_push.sh` runs quality gates + build + push.
- OpenClaw cron calls this script on interval.

## Data sources

The builder reads from OpenClaw workspace/state:
- `DAILY_PLAN.md`
- `TODAY_STATUS.md`
- `memory/YYYY-MM-DD.md`
- `~/.openclaw/cron/jobs.json`
- `scripts/reliability_watchdog_report.py` (health status)

## Reliability and safety design

- Builder is tolerant of missing/corrupt source files (returns safe defaults).
- Dashboard can render partial data if one source fails.
- Publishing is gated by lightweight compile/test checks.

## Extension points

- Add new cards by extending status JSON schema in `status_builder.py` and rendering in `app.js`.
- Add stronger tests in `scripts/tests/` as schema complexity grows.
