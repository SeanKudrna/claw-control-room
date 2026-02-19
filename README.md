# Claw Control Room

A React + TypeScript dashboard (GitHub Pages) that gives a clear window into Claw's day:
- tabbed views (Overview / Operations / Insights / Skills) to prevent a single-page infodump
- sticky section navigation shell for faster movement between tabs on phones (translucent contrast-tuned)
- subtle top/bottom viewport edge fades so scrolling content exits more smoothly
- mobile-first responsive layout tuned for touch usage and phone readability
- collapsible content sections for cleaner UX and faster scanning
- compact panel-body mode to avoid duplicate heading stacks inside collapsible sections
- real-time runtime panel (cron + background/subagent execution only, with live elapsed timers)
- hybrid runtime-truth core: materialized runtime ledger (`status/runtime-state.json`) is preferred when fresh, with deterministic live reconciler fallback when ledger state is missing/stale
- MCP expansion pack scaffold for control-room operations (`issue/status/release/runtime`) and skill-lab capability loops (`discover/learn/level transition`)
- static fallback snapshot is runtime-sanitized (idle-only) to avoid stale `RUNNING` ghost rows when gist/source fetch fails
- per-run runtime details sheet (tap/click row details for source/session/start/elapsed/summary + model + thinking metadata), rendered above sticky layers for consistent readability, with fallback labels when metadata is missing and an explicit baseline check for `gpt-5.3-codex + high`
- data freshness pill (fresh / aging / stale) based on payload generation time, with live age progression between polls
- refresh control is anchored in the sticky tab row (right-aligned with section tabs) with truthfulness states (refreshing, success, explicit failure/retry while retaining last known good snapshot), including clear "fetched but still stale" wording when freshness does not improve
- structured refresh-failure taxonomy (network/http/payload/source) for clearer degraded-mode operator guidance
- strict runtime payload-shape validation before render (malformed snapshots are rejected as `status-payload-invalid` instead of crashing UI assumptions)
- explicit source semantics pill (Live source vs Fallback snapshot) with fallback reason detail for transparent degraded-mode awareness
- fallback behavior hardening: if configured source fails, dashboard automatically falls back to local snapshot and labels the state
- race-safe polling (latest request wins; older/aborted responses cannot overwrite newer status)
- tactile refresh interaction states (press, refreshing spinner, completion confirmation)
- OpenClaw brand-aligned coral/orange/dark gradient palette for visual continuity
- custom lobster favicon + home-screen icons for mobile install branding
- polished interaction states and focus-visible accessibility styling across controls
- current focus and active work (with timeline-aware stale fallback)
- now/next/done swimlanes driven by a unified chronological event model (timeline blocks + scheduled jobs + active runtime), deterministic lane-state transitions, in-progress timeline blocks retained until end-time completion, no cross-lane duplicates, no past items in now/next, done ordering newest-first, and done timestamps shown per item when derivable
- activity feed category noise is normalized (no `N/A` filter/tag clutter; unknown categories map to `OPS`), and `N/A` timestamp pills are suppressed for cleaner chips
- timeline of planned tasks with automatic current-block highlighting (when the local time falls within a listed block range, including `AM/PM` ranges)
- upcoming scheduled jobs
- job + reliability trend mini charts
- filterable activity feed with default condensed view (latest 12) + expand/collapse
- recent findings/wins
- Skills tab now behaves as a full-tab pannable map surface (desktop + mobile), rather than a small inner viewport.
- Skills placement follows a deterministic dependency-aware hub/branch sector model with fixed depth rings and stable ordering (`tier` → `name` → `id`) to prevent refresh jitter.
- Skills map still renders one node per skill domain (no tier-per-card clutter) with connectors behind nodes, subtle depth-guide rings, and readability safeguards (no node overlap/title clipping/node clipping).
- Each domain node now carries three hierarchy layers: concise progression (`Tier X/5`), current-function copy, and next level-up meaning while retaining clear unlocked / in-progress / planned / locked visual states.
- Skills node inspection remains modal-based (click/tap to open details; escape/backdrop/close to dismiss) and now includes current function, next level-up meaning, locked-requirements checklist, and the visual 5-tier ladder (definitions, differences, current highlight, complete tiers, and next unlock).
- Locked-skill modal now includes a `Start Learning` action that launches deterministic background learning jobs (pending -> running -> completed) and updates skill tier/unlock state on completion.
- Skills tree now surfaces per-node learning job state chips (`Queued`, `Running`, `Completed`) with near-real-time transitions while the modal is open.
- Added `Discover New Skill` modal flow that creates candidate locked skills directly in the map as new learnable branches.
- Skills map navigation includes unobtrusive in-map controls for zoom in/out plus a fit/reset view toggle while preserving full-tab map real estate.
- Overflow skill maps continue to support bounded drag-pan (mouse + touch via pointer events), preserving large-canvas navigation without sacrificing modal UX.

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

Issue #50 critical visual QA loop (skills pan/zoom/modal/actions + runtime details metadata):

```bash
npm run build
npm run preview -- --host 127.0.0.1 --port 4173
# in another shell:
node scripts/tests/capture_issue50_screenshots.mjs
node scripts/tests/capture_issue50_job_details_screenshots.mjs
node scripts/tests/test_skill_actions_flow.mjs
```

Proof artifacts are written to `status/ui-validation/issue50-*.png`.

## Issue monitoring / QA workflow

Open-issue snapshot (markdown output):

```bash
python3 scripts/issue_snapshot.py
```

Issue discipline:
- Log defects/improvements as GitHub issues (use issue templates).
- Link ticket-directed commits with `refs #<issue>`.
- Ticket-linked release example:

```bash
./scripts/update_and_push.sh --version 1.2.0 --issue 12 --message "fix: resolve duplicate next-lane items"
```

## Publish modes

### A) Status-only publish (recommended, no repo commit)

```bash
./scripts/publish_status.sh
```

This updates a GitHub Gist payload consumed by the dashboard, so routine status refreshes do **not** create repo commits.
(Automation currently runs every 1 minute during daytime window for tighter runtime freshness.)

### Runtime ledger maintenance (hybrid truth core)

```bash
python3 scripts/runtime/collect_runtime_events.py
python3 scripts/runtime/materialize_runtime_state.py
```

Recommended cadence is 10-15s per step in automation so runtime state remains fresh enough for the status publisher.

### MCP scaffold servers (Block 5)

```bash
python3 scripts/mcp/control_room_mcp_server.py
python3 scripts/mcp/skill_lab_mcp_server.py
```

End-to-end proof runner (Control-Room MCP flow):

```bash
python3 scripts/mcp/run_control_room_mcp_flow.py
```

MCP docs index:
- `docs/mcp/README.md`
- `docs/mcp/control-room-mcp-plan.md`
- `docs/mcp/skill-lab-mcp-plan.md`
- `docs/mcp/runtime-bridge-protocol-draft.md`

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
- `~/.openclaw/workspace/ClawPrime_Memory.md` (skills evolution artifact source)
- `~/.openclaw/workspace/status/runtime-state.json` (preferred materialized runtime truth)
- `~/.openclaw/workspace/status/runtime-events.jsonl` (append-only runtime lifecycle journal)
- `~/.openclaw/agents/main/sessions/sessions.json`
- `~/.openclaw/subagents/runs.json` (background/subagent runtime registry)
- `~/.openclaw/cron/jobs.json`
- `~/.openclaw/cron/runs/*.jsonl`
- `~/.openclaw/workspace/scripts/reliability_watchdog_report.py`
- `~/.openclaw/logs/reliability-watchdog.jsonl`

## Hosting

- GitHub Pages serves from `main` branch `/docs` folder (Vite build output).
- App reads status source config from `public/data/source.json`.
- App fallback snapshot is `public/data/status.json`.
