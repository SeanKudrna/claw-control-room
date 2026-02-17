# Claw Control Room

A React + TypeScript dashboard (GitHub Pages) that gives a clear window into Claw's day:
- current focus and active work (with timeline-aware stale fallback)
- now/next/done swimlanes
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

## Publish modes

### A) Status-only publish (recommended, no repo commit)

```bash
./scripts/publish_status.sh
```

This updates a GitHub Gist payload consumed by the dashboard, so routine status refreshes do **not** create repo commits.

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
