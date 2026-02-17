# Development Guide

## Prereqs
- Node.js 20+
- npm
- Python 3.11+
- GitHub CLI (`gh`) authenticated for publish/release scripts

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
- Python tests (`scripts/tests/test_status_builder.py`, `scripts/tests/test_extract_release_notes.py`)
- status payload build sanity check
- TypeScript typecheck
- Vite production build

## Status-only publish (no commit)

```bash
./scripts/publish_status.sh
```

Use this for routine runtime status refreshes.

## Code/docs release publish (with semver tag + GitHub release)

```bash
./scripts/update_and_push.sh --version 1.0.0 --message "release: v1.0.0"
```

Script behavior:
1. validates semver
2. bumps `package.json`/`package-lock.json` version
3. runs full quality gate
4. commits + pushes
5. tags release (`vX.Y.Z`) and pushes tag
6. creates GitHub release with notes extracted from matching changelog section

## Changelog format expectation

`CHANGELOG.md` should include version headings like:

```md
## v1.0.0 - 2026-02-17
```

Release notes extraction script reads this section and stops at the next `## v...` heading.

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
