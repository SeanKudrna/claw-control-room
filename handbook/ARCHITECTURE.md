# Architecture

## Purpose
Claw Control Room provides a readable, near-real-time view of Claw's operations:
- current focus / active work
- now/next/done swimlanes
- planned timeline + upcoming jobs
- reliability posture and trend
- activity feed and findings
- game-style skills progression map (connected branches + tier hierarchy) with deterministic evolution inputs

## High-level design

### 1) Data generation + publish (Python)
- `scripts/build_status_json.py` is the CLI entrypoint for local snapshot generation.
- Core payload assembly lives in `scripts/lib/status_builder.py`.
- Skills payload assembly is deterministic (`build_skills_payload`): keyword-weighted extraction from `memory/YYYY-MM-DD.md` + `ClawPrime_Memory.md` builds one node per skill domain, computes current tier progression (`Tier X/5`), emits per-domain tier-ladder metadata (definitions + difference copy for tiers 1..5), and records evolution metadata (source artifact list + deterministic seed).
- Payload builder applies timeline-aware stale-guard logic so `currentFocus` and `workstream.now` stay accurate even when `TODAY_STATUS.md` lags behind clock time.
- Workstream now/next/done is built from a unified chronological event model: timeline blocks (`DAILY_PLAN`), scheduled jobs (`nextRunAtMs`), and active runtime rows.
- Deterministic lane-state rules define `now`, `next`, and `done` transitions (including day reset), removing ad-hoc stale carryover behavior.
- `now` resolves to current runtime activity when present; otherwise the earliest not-yet-completed scheduled event (including in-progress timeline blocks until end time).
- `next` is the ordered remainder after `now`, with no past/completed items.
- `done` starts empty each day and only receives items that first appeared in `now` and later completed (end-time reached), rendered newest-first for scanability.
- Done items expose leading completion-time prefixes when time is derivable, improving recency scanning in Overview.
- Runtime truth now uses a hybrid model:
  - Preferred source: materialized runtime ledger (`status/runtime-state.json`) produced from append-only runtime events.
  - Fallback source: deterministic live reconciler over sessions store + cron terminal logs + subagent registry.
- Reconciler guarantees terminal dominance (`finished/failed/cancelled/timed_out`) and stale-orphan expiry TTL before rendering active rows.
- Runtime payload now surfaces provenance metadata (`source`, `revision`, `snapshotMode`, `degradedReason`) plus per-run execution metadata (`model`, `thinking` when available) so operators can see whether truth is materialized, reconciled, or fallback-sanitized and what execution profile is currently in flight.
- Runtime semantics intentionally exclude main/interactive rows (cron + background/subagent only).
- Control-room status publisher runs are intentionally excluded from runtime activity to avoid self-referential false-running states.
- `scripts/runtime/collect_runtime_events.py` appends normalized lifecycle events into `status/runtime-events.jsonl` (idempotent eventId guard).
- `scripts/runtime/materialize_runtime_state.py` replays the journal into `status/runtime-state.json` with monotonic runtime revision.
- `scripts/publish_status_gist.py` pushes fresh payloads to a GitHub Gist.
- `scripts/publish_status.sh` is the operational wrapper used by cron.

### 2) Dashboard UI (React + TypeScript + Vite)
- App source: `src/`
  - `src/components/` presentation modules
  - `src/hooks/useStatus.ts` polling + load state + refresh outcome/freshness aging logic
  - `src/lib/statusApi.ts` source resolution/fetch logic
  - `src/types/status.ts` shared payload contracts
- Information architecture uses tabbed views (`Overview`, `Operations`, `Insights`, `Skills`) plus collapsible sections to reduce visual overload.
- Global Command Center palette (`Ctrl/Cmd+K`) sits above tab views and indexes tabs + timeline blocks + upcoming jobs + activity + findings with keyboard-first navigation.
- Skills tab renders as a full-tab pannable map surface using a custom SVG+DOM layout engine (`src/lib/skillTreeLayout.ts`) instead of a React graph runtime, prioritizing visual quality, deterministic structure, and lightweight bundle impact.
- Layout engine now uses explicit dependency-aware hub/branch sectors: dependency-free domains become root hubs, first-hop descendants become branch anchors, and deeper nodes expand on fixed depth rings. Ordering is deterministic (`tier` → `name` → `id`) so positions are refresh-stable (no jitter).
- Main graph renders one node per domain and keeps connectors in an SVG layer beneath interactive cards to avoid line/text collisions; ring spacing + angle separation are tuned to prevent node overlap and clipping.
- Branch readability is reinforced with subtle depth-guide rings (rendered in the SVG layer) so outward hierarchy remains legible while preserving map focus.
- Node chrome now exposes three meaning layers: progression (`Tier X/5` + state), current-function copy, and next level-up meaning.
- Skill details are presented in a modal dialog (not a persistent side panel), preserving map real estate while exposing current function, next level-up meaning, locked-requirements checklist, and a visual tier ladder (tiers 1..5 definitions, current-tier highlight, complete tiers, and next unlock guidance).
- Skills modal now includes an interactive action layer (`Start Learning`, `Discover New Skill`) powered by deterministic local job orchestration (`src/lib/skillActions.ts`).
- Learning jobs transition `pending -> running -> completed` in near real time, and completed jobs deterministically promote skill tier/level/unlock state.
- Discover flow creates candidate locked skills as new map nodes, chained to the selected source skill as a dependency branch.
- Overflow map navigation pairs pointer-driven bounded drag-pan (mouse + touch) with in-map zoom controls (`+`, `-`, fit/reset) so operators can quickly move between broad orientation and detail inspection without leaving the full-tab surface.
- Components rendered inside collapsible bodies support compact heading mode, so section titles stay in the summary row while inner content keeps accessibility labels without duplicate heading stacks.
- Active tab is URL-hash persisted (`#tab-*`) for direct navigation/state restore.
- Theme tokens align to OpenClaw website palette conventions (deep dark surface + coral/orange accents) for product continuity.
- Branding assets (favicon/home-screen icons + manifest) are served from `public/icons/` and linked in `index.html`.
- Interaction system standardizes hover/active/focus-visible states across tabs, chips, refresh, and collapsible summaries for UX coherence.
- Timeline current-block rendering supports both 24-hour and `AM/PM` ranges so highlight state is reflected in visible UI (not just computed logic).
- Activity Feed normalizes unknown/`N/A` category values into `ops` so filter chips and badges remain clean and actionable, and suppresses `N/A` timestamp pills in feed metadata.
- Runtime details modal is rendered through a `document.body` portal so it always layers above sticky headers and card stacking contexts, and now includes run-time model + thinking metadata with explicit fallback messaging plus a baseline check target (`gpt-5.3-codex + high`).
- Viewport edge-fade scrims (top/bottom) are rendered as fixed non-interactive overlays to soften scroll exits without affecting input hit targets.
- Build output: `docs/` (served by GitHub Pages).

### 3) Status source strategy
- Primary runtime source: Gist URL from `public/data/source.json`.
- Runtime internals prefer fresh materialized ledger state and drop to live reconciler only when ledger state is missing/stale/invalid.
- Fallback source: `public/data/status.json`.
- Fallback payload is runtime-sanitized (`idle`, no active runs) with explicit runtime metadata (`source=fallback-static`, `snapshotMode=fallback-sanitized`) so cached/static fallback cannot present stale `RUNNING` activity.
- Frontend polling keeps showing the last known good snapshot when refresh fails, and sticky tab-row refresh state explicitly marks failure/retry instead of implying success.
- Polling is concurrency-safe: every refresh gets a monotonic request sequence and abort controller; only the newest successful request may commit state.
- Aborted superseded requests are intentionally silent (no false error banners) to avoid degraded-noise during quick retry/manual refresh patterns.
- Refresh failures are normalized into stable error codes (network/http/payload/source) so UI copy can distinguish failure class while preserving last-known-good behavior.
- Payload fetch now includes runtime shape validation for required top-level containers/fields; malformed JSON objects are rejected as `status-payload-invalid` before UI state commit.
- Header now surfaces explicit source semantics (`Live source` vs `Fallback snapshot`) with fallback-reason detail so operators can see when they're in degraded mode even if data still loads.
- Fallback behavior is fail-soft: configured source fetch attempts first, then local fallback snapshot is used when primary is unavailable/invalid.
- Freshness age is recomputed on a timer between polls so stale data visibly ages even if payload timestamp is unchanged.
- Refresh success copy distinguishes "updated" from "fetched but still stale" states to prevent false confidence when the newest available snapshot is still old.
- Overview now includes a compact Refresh Diagnostics panel exposing latest refresh outcome, source mode, freshness age, and persisted last-error metadata for fast degraded-mode triage.
- Sticky tab-row refresh control is button-only (no helper text beneath it) to keep row rhythm tight and reduce duplicate messaging.
- This preserves commitless status refreshes while keeping a safe local fallback snapshot and honest degraded-state UX.

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
- Critical UI milestones use focused Playwright proof capture loops (for issue #50: skills map fit/zoom/modal flows + runtime details metadata fallback), with artifacts stored under `status/ui-validation/`.
- This keeps dashboard evolution visible, triaged, and linked to implementation commits.

### 6) MCP integration scaffold (Issue #50 Block 5)
- `scripts/mcp/control_room_mcp_server.py` exposes control-room operational actions as MCP tools:
  - `control-room.issue.snapshot`
  - `control-room.status.build`
  - `control-room.release.extract-notes`
  - `control-room.runtime.materialize`
- `scripts/mcp/skill_lab_mcp_server.py` provides Skill-Lab capability scaffolding for discover/learn/level transitions:
  - `skill-lab.state.get`
  - `skill-lab.discover`
  - `skill-lab.learn.start`
  - `skill-lab.level.transition`
- Both servers use JSON-RPC stdio framing helpers in `scripts/mcp/jsonrpc_stdio.py` and can be tested through the e2e proof runner `scripts/mcp/run_control_room_mcp_flow.py`.
- Runtime-Bridge low-latency sync contract draft is documented in `docs/mcp/runtime-bridge-protocol-draft.md`.

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
