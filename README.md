# Claw Control Room

A React + TypeScript dashboard (GitHub Pages) that gives a clear window into Claw's day:
- tabbed views (Overview / Operations / Insights) to prevent a single-page infodump
- collapsible content sections for cleaner UX and faster scanning
- compact panel-body mode to avoid duplicate heading stacks inside collapsible sections
- real-time runtime panel (idle vs running, active job list, live elapsed timers)
- data freshness pill (fresh / aging / stale) based on payload generation time
- tactile refresh interaction states (press, refreshing spinner, completion confirmation)
- current focus and active work (with timeline-aware stale fallback)
- now/next/done swimlanes (next lane dedupes overlapping timeline/status blocks using time overlap + token overlap)
- timeline of planned tasks
- upcoming scheduled jobs
- job + reliability trend mini charts
- filterable activity feed
- recent findings/wins

## Standards

This repo follows a strict engineering contract in `AGENTS.md`:
- modular code first
- docs updated with every meaningful behavior change
- quality gates before push
- semantic versioning + release tags

Read next:
- `handbook/ARCHITECTURE.md`
- `handbook/DEVELOPMENT.md`
- `CHANGELOG.md`

## Local development

```bash
npm install
npm run dev
```

## Full quality gate

```bash
./scripts/quality_gate.sh
```

## Issue monitoring / QA workflow

Open-issue snapshot (markdown output):

```bash
python3 scripts/issue_snapshot.py
```

Issue discipline:
- Log defects/improvements as GitHub issues (use issue templates).
- Link ticket-directed commits with `refs #<issue>`.
- Ticket-linked release example:

```bash
./scripts/update_and_push.sh --version 1.2.0 --issue 12 --message "fix: resolve duplicate next-lane items"
```

## Publish modes

### A) Status-only publish (recommended, no repo commit)

```bash
./scripts/publish_status.sh
```

This updates a GitHub Gist payload consumed by the dashboard, so routine status refreshes do **not** create repo commits.
(Automation currently runs every 1 minute during daytime window for tighter runtime freshness.)

### B) Code/docs release publish (commit + tag + GitHub release)

```bash
./scripts/update_and_push.sh --version 1.0.0 --message "release: v1.0.0"
```

This workflow:
1. bumps internal app version
2. runs quality gate
3. commits + pushes
4. creates/pushes tag (`vX.Y.Z`)
5. creates GitHub release from matching changelog section

## Data sources

Runtime status builder reads from:
- `~/.openclaw/workspace/DAILY_PLAN.md`
- `~/.openclaw/workspace/TODAY_STATUS.md`
- `~/.openclaw/workspace/memory/YYYY-MM-DD.md`
- `~/.openclaw/cron/jobs.json`
- `~/.openclaw/workspace/scripts/reliability_watchdog_report.py`
- `~/.openclaw/logs/reliability-watchdog.jsonl`

## Hosting

- GitHub Pages serves from `main` branch `/docs` folder (Vite build output).
- App reads status source config from `public/data/source.json`.
- App fallback snapshot is `public/data/status.json`.
