# Changelog

## v1.4.10 - 2026-02-17

### Fixed
- Runtime no longer drops to false `IDLE` during in-flight main-session execution before tool results arrive.

### Changed
- Main-session runtime detection now considers assistant `toolCall` events in addition to `toolResult` events.
- Added session-lock awareness to keep active main-session task runs visible while execution is in progress.

### Added
- Tests for in-flight `toolCall`-only detection and stale signal suppression without active lock.

## v1.4.9 - 2026-02-17

### Changed
- Tuned sticky tab header to be less opaque while preserving button contrast.
- Added subtle fixed top/bottom viewport fade overlays so scrolling content dims out near screen edges instead of hard-cutting.

## v1.4.8 - 2026-02-17

### Changed
- Runtime monitor now includes active main-session task execution (tool-driven) alongside cron + subagent work.
- Main-session runtime detection explicitly ignores chat-only turns, preventing `RUNNING` just from conversation.
- Runtime source labels now include `Main` for direct session work.

### Added
- Test coverage for main-session runtime detection (task/tool-positive + chat-only-negative paths).

## v1.4.7 - 2026-02-17

### Changed
- Increased sticky tab-shell contrast with a darker translucent backdrop and stronger separation shadow.
- Slightly boosted inactive tab text/background contrast for easier button visibility on mobile.

## v1.4.6 - 2026-02-17

### Fixed
- Stabilized the page background gradient so collapsing/expanding sections no longer reflows the full background based on document height.
- Removed the mobile short-page "squared footer" band by pinning gradient rendering to a fixed viewport layer with full-viewport shell sizing.

## v1.4.5 - 2026-02-17

### Improved
- Runtime background labels now fall back to task summaries when labels are generic, reducing vague `Background task` rows.
- Runtime details sheet polish: source type shows friendly label (`Cron`/`Background`), and detail actions include tighter accessibility semantics.
- Runtime source badges now align to the warm coral palette for visual consistency.

## v1.4.4 - 2026-02-17

### Changed
- Polished information hierarchy and spacing rhythm across dashboard cards/panels for cleaner scanability (updated card density, section spacing, panel content rhythm).
- Made section navigation more mobile-friendly with a sticky tab shell and improved horizontal tab snap behavior.
- Refined Activity Feed readability: clearer meta/text separation per row plus a default condensed window (latest 12) with optional expand/collapse.
- Improved Operations jobs readability with stronger time/job/status emphasis in both table and small-screen card layouts.
- Runtime UX pass (#15): active rows now use more descriptive background labels when metadata exists, and each row provides an accessible click/tap details sheet with source type, session id/key, started time, elapsed time, and task summary.

### Docs
- Updated README feature list to reflect sticky mobile tab navigation and condensed Activity Feed behavior.

## v1.4.3 - 2026-02-17

### Fixed
- Runtime panel now reports background activity only: cron runs + active subagent/background tasks.
- Foreground chat heartbeat (`agent:main:main`) is excluded so chatting does not falsely show `RUNNING`.

## v1.4.2 - 2026-02-17

### Fixed
- Rebuilt lobster favicon/home-screen icon set with full-bleed, high-contrast artwork so iOS home-screen installs show a clear, properly filled icon tile.

### Changed
- Shifted UI accents from cyan-forward to OpenClaw-style coral/orange/red gradients across interactive controls and runtime surfaces.
- Updated app/theme metadata colors to match the warmer brand direction on mobile home-screen/PWA chrome.

## v1.4.1 - 2026-02-17

### Fixed
- Runtime activity now includes recent main-session heartbeat detection so the dashboard reflects interactive work (not cron-only), with cron vs interactive source labels.

## v1.4.0 - 2026-02-17

### Added
- Refresh button now has tactile interaction states: press feedback, active spinner state while fetching, and short post-refresh confirmation.
- Added reduced-motion-safe handling for refresh/collapse animations.
- Added custom lobster favicon set (SVG + PNG + `.ico`) and mobile home-screen icon metadata/manifest wiring.

### Changed
- Reworked responsive behavior with a mobile-first pass: touch-friendly control sizing, horizontal tab scroller, stacked runtime/cards, safe-area padding, and mobile-optimized jobs table layout.
- Shifted the dashboard color system to match OpenClaw website palette conventions (deep dark surfaces + coral/cyan accents).
- Added final UX polish pass for consistent hover/focus/active states, improved control transitions, and stronger keyboard accessibility visibility.

## v1.3.3 - 2026-02-17

### Fixed
- Removed duplicate heading stacks inside collapsible panel bodies by adding compact heading mode to panel content components.
- Preserved accessibility labels for compacted panel-body sections while keeping section titles in the collapsible summary row.

### Added
- Added UI contract test `scripts/tests/test_collapsible_heading_compact.py` to ensure collapsible panel bodies keep heading compaction wired in `App.tsx`.

### Changed
- Updated docs to document collapsible compact-heading behavior and quality gate coverage.

## v1.3.2 - 2026-02-17

### Fixed
- Deduplicated overlapping timeline/status entries in the Overview next lane using time-range overlap plus semantic matching.
- Refined next-lane dedupe to treat overlapping time ranges with meaningful token overlap as duplicates.

## v1.3.1 - 2026-02-17

### Fixed
- Resolved runtime panel false-running state caused by self-referential status publisher detection.
- Excluded control-room status publish job from runtime active-run calculation to prevent sticky `RUNNING` status.

### Changed
- Increased status publish cadence from every 5 minutes to every 1 minute for tighter runtime freshness.
- Added test coverage for runtime exclusion logic.

## v1.3.0 - 2026-02-17

### Added
- Real-time runtime monitor panel in Overview:
  - `IDLE` vs `RUNNING` state
  - active background job list
  - live elapsed timers per run (`HH:MM:SS`)
- Runtime payload contract (`runtime`) with source metadata and active run details.
- Runtime detection test coverage in `test_status_builder.py`.

### Changed
- Status builder now derives active runs by reconciling session-store run keys against cron finished-run logs.
- Type contracts updated for runtime observability fields.

## v1.2.0 - 2026-02-17

### Added
- GitHub issue templates for QA defects and product improvements (`.github/ISSUE_TEMPLATE/*`).
- Issue backlog snapshot script (`scripts/issue_snapshot.py`) with markdown output for planning reviews.
- Issue-snapshot test coverage (`scripts/tests/test_issue_snapshot.py`).

### Changed
- Release script now supports `--issue <id>` and appends `refs #<id>` to ticket-directed commit messages.
- Quality gate expanded to compile/test issue snapshot tooling.
- Documentation updated with issue-driven QA workflow and ticket-linked release examples.

## v1.1.0 - 2026-02-17

### Added
- Tabbed information architecture with dedicated dashboard views:
  - Overview
  - Operations
  - Insights
- Collapsible section containers for major content groups to reduce on-screen overload.
- URL hash tab persistence (`#tab-overview`, `#tab-operations`, `#tab-insights`) for direct navigation.

### Changed
- Reorganized app layout to avoid single-page info-dump and improve scanability.
- Styled UI controls for tabs/collapsible behavior with responsive mobile behavior.

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
