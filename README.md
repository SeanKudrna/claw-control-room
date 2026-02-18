# Claw Control Room

A React + TypeScript dashboard (GitHub Pages) that gives a clear window into Claw's day:
- tabbed views (Overview / Operations / Insights / Skills) to prevent a single-page infodump
- sticky section navigation shell for faster movement between tabs on phones (translucent contrast-tuned)
- subtle top/bottom viewport edge fades so scrolling content exits more smoothly
- mobile-first responsive layout tuned for touch usage and phone readability
- collapsible content sections for cleaner UX and faster scanning
- compact panel-body mode to avoid duplicate heading stacks inside collapsible sections
- real-time runtime panel (cron + background/subagent execution only, with live elapsed timers)
- static fallback snapshot is runtime-sanitized (idle-only) to avoid stale `RUNNING` ghost rows when gist/source fetch fails
- per-run runtime details sheet (tap/click row details for source/session/start/elapsed/summary), rendered above sticky layers for consistent readability
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
- Skills tab now renders as a full-width radial/branching game-style tree: dependency connectors stay behind nodes, hierarchy expands outward by tier, and node visuals clearly separate unlocked / in-progress / planned / locked states.
- Skills tree uses a custom deterministic SVG+DOM layout (instead of a graph library) for faster load, easier visual control, and stricter readability guarantees (no node overlap/title clipping).
- Skills node inspection is now modal-based (click/tap to open details, escape/backdrop/close button to dismiss) so the tree retains full canvas width.
- Overflow skill maps support drag-pan (mouse + touch via pointer events) to preserve exploration/readability on desktop and mobile.

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
- `~/.openclaw/agents/main/sessions/sessions.json`
- `~/.openclaw/subagents/runs.json` (background/subagent runtime registry)
- `~/.openclaw/subagents/runs.json`
- `~/.openclaw/cron/jobs.json`
- `~/.openclaw/cron/runs/*.jsonl`
- `~/.openclaw/workspace/scripts/reliability_watchdog_report.py`
- `~/.openclaw/logs/reliability-watchdog.jsonl`

## Hosting

- GitHub Pages serves from `main` branch `/docs` folder (Vite build output).
- App reads status source config from `public/data/source.json`.
- App fallback snapshot is `public/data/status.json`.
