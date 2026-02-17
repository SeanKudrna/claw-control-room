# Changelog

## v1.0.2 - 2026-02-17

### Fixed
- Filtered stale time-ranged items out of the `Next` swimlane when those blocks have already ended.
- Prevented old `Next 3 meaningful blocks` entries from `TODAY_STATUS.md` from reappearing after their time window passes.

### Added
- Test coverage for stale-next-item filtering in `parse_workstream`.

## v1.0.1 - 2026-02-17

### Fixed
- Corrected stale status behavior where `Current Focus` could show `n/a` and `Now` could remain on an old time block.
- Added timeline-aware fallback logic so runtime `activeWork/currentFocus/workstream.now` reflect the current DAILY_PLAN window when TODAY_STATUS is stale.
- Added stale-guard for `Running now` time ranges to prevent outdated blocks from persisting on the dashboard.

### Added
- Expanded test coverage for stale active-work fallback and timeline-aware workstream rendering.

## v1.0.0 - 2026-02-17

### Added
- Upgraded dashboard UX with:
  - now/next/done swimlane board
  - mini trend charts (job success + reliability trend)
  - filterable activity feed with category chips
- Version visibility in UI header (`vX.Y.Z`) sourced from runtime payload.
- Release-notes extraction utility (`scripts/extract_release_notes.py`) + tests.
- Release-aware push workflow in `scripts/update_and_push.sh`:
  - semver bump
  - commit/push
  - tag creation/push
  - GitHub release creation from changelog notes

### Changed
- Expanded payload contract in `scripts/lib/status_builder.py` with:
  - `controlRoomVersion`
  - `workstream` lanes
  - `charts` data series
  - `activity` feed records
- `scripts/build_status_json.py` now writes fallback snapshot to `public/data/status.json`.
- Quality gate now covers release-note extraction tests.
- Documentation updated to formalize semver + release workflow.

### Ops
- GitHub Pages remains served from `main:/docs`.
- Commitless gist-based status publishing remains default for runtime refreshes.

## v0.2.0 - 2026-02-17

### Added
- React + TypeScript frontend architecture (`src/`) with modular components/hooks/lib/types.
- Vite build pipeline with GitHub Pages output to `docs/`.
- Frontend status API resolver (`src/lib/statusApi.ts`) with gist-first + local fallback strategy.
- Engineering contract for long-term maintainability (`AGENTS.md`).
- Expanded architecture/development handbook docs (`handbook/ARCHITECTURE.md`, `handbook/DEVELOPMENT.md`).
- Quality gate script (`scripts/quality_gate.sh`) covering Python checks + TS typecheck + production build.
- Commitless status publish path (`scripts/publish_status.sh`, `scripts/publish_status_gist.py`).

### Changed
- Refactored from static vanilla JS UI to React + TypeScript for scalability and easier agent collaboration.
- Updated publish strategy:
  - status refreshes -> gist updates (no commit spam)
  - code/docs changes -> commit + push via `scripts/update_and_push.sh`
- Updated docs references from `docs/` source docs to `handbook/` (with `docs/` now reserved for built site artifacts).

### Ops
- GitHub Pages configured to serve built static artifacts from `main:/docs`.
- Control room runtime status auto-refresh remains cron-driven via gist backend.
