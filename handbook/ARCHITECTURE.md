# Architecture

## Purpose
Claw Control Room provides a readable, near-real-time view of Claw's operations:
- current focus
- active work block
- planned timeline
- upcoming scheduled jobs
- recent findings/wins

## High-level design

### 1) Data generation + publish (Python)
- `scripts/build_status_json.py` is the CLI entrypoint.
- Core logic lives in `scripts/lib/status_builder.py`.
- `scripts/publish_status_gist.py` pushes fresh status payloads to a GitHub Gist.
- `scripts/publish_status.sh` is the operational wrapper used by cron.

### 2) Dashboard UI (React + TypeScript + Vite)
- App source: `src/`
  - `src/components/` presentation components
  - `src/hooks/useStatus.ts` polling + state
  - `src/lib/statusApi.ts` source resolution/fetch logic
  - `src/types/status.ts` shared status payload contracts
- Build output: `docs/` (served by GitHub Pages).

### 3) Status source strategy
- Primary runtime source: Gist URL from `public/data/source.json`.
- Fallback source: `public/data/status.json` (last-known sample snapshot).
- This avoids repo commit spam for routine status refreshes.

## Build and delivery flow

### Status-only refresh (default)
1. Cron triggers `scripts/publish_status.sh`.
2. Script builds latest payload from workspace + cron state.
3. Script updates gist JSON.
4. Dashboard fetches fresh gist data on load/refresh.

### Code/docs changes
1. Update source in `src/`, `scripts/`, or `handbook/`.
2. Run `./scripts/quality_gate.sh`.
3. Run `./scripts/update_and_push.sh`.
4. GitHub Pages serves updated build from `docs/`.

## Reliability and safety notes
- Builder is resilient to missing/invalid local source files (safe defaults).
- Quality gate enforces Python checks + TS typecheck + production build.
- Docs/changelog updates are required whenever behavior/contracts change.

## Extension points
- Add cards/panels by extending:
  - payload schema in `scripts/lib/status_builder.py`
  - typed contracts in `src/types/status.ts`
  - UI rendering in `src/components/`
- Add tests under `scripts/tests/` and (if needed) frontend tests in a future `src/tests/` layer.
