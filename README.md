# Claw Control Room

A React + TypeScript dashboard (GitHub Pages) that gives a clear window into Claw's day:
- current focus
- active work block
- timeline of planned tasks
- next scheduled jobs
- recent findings/wins

## Standards

This repo follows a strict engineering contract in `AGENTS.md`:
- modular code first
- docs updated with every meaningful behavior change
- quality gates before push

Read next:
- `handbook/ARCHITECTURE.md`
- `handbook/DEVELOPMENT.md`
- `CHANGELOG.md`

## Local development

```bash
npm install
npm run dev
```

## Build + typecheck

```bash
./scripts/quality_gate.sh
```

## Publish modes

### A) Status-only publish (recommended, no repo commit)

```bash
./scripts/publish_status.sh
```

This updates a GitHub Gist payload consumed by the dashboard, so routine status refreshes do **not** create repo commits.

### B) Code/docs publish (commit + push)

```bash
./scripts/update_and_push.sh "optional commit message"
```

Use this when code, docs, or architecture changes.

## Data sources

Runtime status builder reads from:
- `~/.openclaw/workspace/DAILY_PLAN.md`
- `~/.openclaw/workspace/TODAY_STATUS.md`
- `~/.openclaw/workspace/memory/YYYY-MM-DD.md`
- `~/.openclaw/cron/jobs.json`
- `~/.openclaw/workspace/scripts/reliability_watchdog_report.py`

## Hosting

- GitHub Pages serves from `main` branch `/docs` folder (built output from Vite).
- App reads status source config from `public/data/source.json`.
