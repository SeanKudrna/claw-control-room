# Architecture

## Purpose
Claw Control Room provides a readable, near-real-time view of Claw's operations:
- current focus / active work
- now/next/done swimlanes
- planned timeline + upcoming jobs
- reliability posture and trend
- activity feed and findings

## High-level design

### 1) Data generation + publish (Python)
- `scripts/build_status_json.py` is the CLI entrypoint for local snapshot generation.
- Core payload assembly lives in `scripts/lib/status_builder.py`.
- Payload builder applies timeline-aware stale-guard logic so `currentFocus` and `workstream.now` stay accurate even when `TODAY_STATUS.md` lags behind clock time.
- Workstream `next` lane uses time-range overlap plus semantic/token overlap to dedupe overlapping timeline/status items, keeping timeline blocks canonical.
- Runtime detection reconciles session-store cron run keys against cron finished logs, and treats recent main-session heartbeats (3-minute window) as interactive activity; runtime rows include a source type (cron vs interactive).
- Control-room status publisher runs are intentionally excluded from runtime activity to avoid self-referential false-running states.
- `scripts/publish_status_gist.py` pushes fresh payloads to a GitHub Gist.
- `scripts/publish_status.sh` is the operational wrapper used by cron.

### 2) Dashboard UI (React + TypeScript + Vite)
- App source: `src/`
  - `src/components/` presentation modules
  - `src/hooks/useStatus.ts` polling + load state
  - `src/lib/statusApi.ts` source resolution/fetch logic
  - `src/types/status.ts` shared payload contracts
- Information architecture uses tabbed views (`Overview`, `Operations`, `Insights`) plus collapsible sections to reduce visual overload.
- Components rendered inside collapsible bodies support compact heading mode, so section titles stay in the summary row while inner content keeps accessibility labels without duplicate heading stacks.
- Active tab is URL-hash persisted (`#tab-*`) for direct navigation/state restore.
- Theme tokens align to OpenClaw website palette conventions (deep dark surface + coral/orange accents) for product continuity.
- Branding assets (favicon/home-screen icons + manifest) are served from `public/icons/` and linked in `index.html`.
- Interaction system standardizes hover/active/focus-visible states across tabs, chips, refresh, and collapsible summaries for UX coherence.
- Build output: `docs/` (served by GitHub Pages).

### 3) Status source strategy
- Primary runtime source: Gist URL from `public/data/source.json`.
- Fallback source: `public/data/status.json`.
- This preserves commitless status refreshes while keeping a safe local fallback snapshot.

### 4) Versioning + release architecture
- Dashboard version lives in `package.json` and is surfaced in UI via payload (`controlRoomVersion`).
- Releases are semver-based (`major.minor.patch`) and tied to git tags + GitHub releases.
- `scripts/update_and_push.sh` is the canonical release path:
  1. bump version
  2. run quality gate
  3. commit + push
  4. create/push `vX.Y.Z` tag
  5. create GitHub release using notes extracted from `CHANGELOG.md`
- For ticket-targeted work, pass `--issue <id>` so release commit messages include `refs #<id>`.

### 5) Continuous QA + issue loop
- QA findings are tracked as first-class GitHub issues (bug + UX/improvement templates).
- `scripts/issue_snapshot.py` writes a markdown backlog snapshot for planning/review.
- This keeps dashboard evolution visible, triaged, and linked to implementation commits.

## Build and delivery flow

### Status-only refresh (default)
1. Cron triggers `scripts/publish_status.sh`.
2. Script builds latest payload from workspace + cron state.
3. Script updates gist JSON.
4. Dashboard fetches fresh gist data on load/refresh.

### Code/docs release publish
1. Implement changes in `src/`, `scripts/`, `public/`, or `handbook/`.
2. Update changelog section for target version.
3. Run `./scripts/update_and_push.sh --version X.Y.Z --message "release: vX.Y.Z"`.

## Reliability and safety notes
- Builder is resilient to missing/invalid local source files (safe defaults).
- Quality gate enforces Python checks + TS typecheck + production build.
- Docs/changelog updates are mandatory whenever behavior/contracts change.

## Extension points
- Add cards/panels by extending:
  - payload schema in `scripts/lib/status_builder.py`
  - typed contracts in `src/types/status.ts`
  - UI rendering in `src/components/`
- Add deeper tests under `scripts/tests/` and future frontend tests under `src/tests/`.
