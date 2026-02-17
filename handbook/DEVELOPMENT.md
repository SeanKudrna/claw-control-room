# Development Guide

## Prereqs
- Node.js 20+
- npm
- Python 3.11+
- GitHub CLI (`gh`) authenticated for publish scripts

## Local frontend dev

```bash
cd ~/.openclaw/workspace/claw-control-room
npm install
npm run dev
```

## Build output for GitHub Pages

```bash
npm run build
```

Vite outputs static artifacts to `docs/`.

## Full quality gate

```bash
./scripts/quality_gate.sh
```

This runs:
- Python compile checks
- Python unit tests (`scripts/tests/test_status_builder.py`)
- Status payload build sanity check
- TypeScript typecheck
- Vite production build

## Status-only publish (no commit)

```bash
./scripts/publish_status.sh
```

Use this for routine runtime status refreshes.

## Code/docs publish (commit + push)

```bash
./scripts/update_and_push.sh "optional commit message"
```

Use this for code, architecture, or UI changes.

## Operational notes
- Dashboard data source config: `public/data/source.json`
- Fallback payload: `public/data/status.json`
- If status publish fails, check:
  - `gh auth status`
  - gist ID in `.gist_id`
  - cron run logs for publish job

## Documentation discipline
Any meaningful behavior/contract change must update:
- `README.md`
- `handbook/ARCHITECTURE.md`
- `handbook/DEVELOPMENT.md`
- `CHANGELOG.md`
