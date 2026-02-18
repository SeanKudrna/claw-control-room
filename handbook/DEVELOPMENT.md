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

UI nav notes:
- Tabs are hash-driven (`#tab-overview`, `#tab-operations`, `#tab-insights`).
- Major sections are collapsible via native `<details>` wrappers.
- Sticky tab shell uses a translucent contrast layer; viewport edge-fade overlays are fixed and non-interactive.
- Status header refresh feedback should remain attempt-accurate (`refreshing` / `success` / `error`) and never report success for failed polls.
- Polling/state updates are latest-wins: superseded requests must be aborted/ignored so stale responses cannot overwrite newer snapshots.
- Aborted/superseded requests should not surface user-visible error banners.
- Refresh failures should map to stable error taxonomy (`status-network-error`, `status-http-error`, `status-payload-invalid`, `status-url-unavailable`) so degraded-state messaging is actionable.
- Status payloads must pass runtime shape validation before commit to UI state; malformed objects should surface `status-payload-invalid` and retain last-known-good snapshot behavior.
- Header source indicator should remain truthful (`Live source` vs `Fallback snapshot`) with fallback reason detail available from the latest fetch path.
- If configured source fetch fails, fetch logic should attempt local fallback snapshot and explicitly mark fallback mode.
- Freshness labels should age on a timer between polls (truthful stale-state progression).
- `Running now` stale-guard should expire single-time completed entries (not just explicit ranges).
- `Next` lane should prefer future timed items; untimed carryover from status notes should only appear when no better timed source exists.
- If timeline `next` blocks are far away, near-term scheduled jobs should be promoted into `next` lane to keep Overview aligned with Operations job schedule.
- `Done` lane should exclude proof/evidence scaffolding bullets, auto-expire stale timestamped completions, and render newest completions first.
- Refresh success helper text should explicitly call out stale carryover when the newest available payload is still old.
- Runtime details modal should render via body portal with z-index above sticky tab/header layers.

## Build output for GitHub Pages

```bash
npm run build
```

Vite outputs static artifacts to `docs/`.

## Status snapshot build helper

```bash
python3 scripts/build_status_json.py
```

Default output is static-fallback-safe (runtime sanitized to idle).
Use live runtime rows only when explicitly needed:

```bash
python3 scripts/build_status_json.py --live-runtime
```

## Full quality gate

```bash
./scripts/quality_gate.sh
```

This runs:
- Python compile checks
- Python tests (`scripts/tests/test_status_builder.py`, `scripts/tests/test_extract_release_notes.py`, `scripts/tests/test_issue_snapshot.py`, `scripts/tests/test_collapsible_heading_compact.py`)
- status payload build sanity check (includes unified event-model lane builder for now/next/done with deterministic transitions/day reset and runtime detection wiring for cron + subagent only)
- TypeScript typecheck
- Vite production build

## Status-only publish (no commit)

```bash
./scripts/publish_status.sh
```

Use this for routine runtime status refreshes.
In production cron, this runs on a 1-minute cadence for tighter runtime monitor freshness.

## Issue snapshot / backlog check

```bash
python3 scripts/issue_snapshot.py
```

Writes a planning-friendly markdown snapshot to:
- `~/.openclaw/workspace/status/control-room-issues.md`

## Code/docs release publish (with semver tag + GitHub release)

```bash
./scripts/update_and_push.sh --version 1.0.0 --message "release: v1.0.0"
```

Ticket-linked release example:

```bash
./scripts/update_and_push.sh --version 1.0.1 --issue 34 --message "fix: resolve stale next-lane duplication"
```

Script behavior:
1. validates semver
2. optional `--issue` validates numeric issue id and appends `(refs #<id>)` to commit message
3. bumps `package.json`/`package-lock.json` version
4. runs full quality gate
5. commits + pushes
6. tags release (`vX.Y.Z`) and pushes tag
7. creates GitHub release with notes extracted from matching changelog section

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
