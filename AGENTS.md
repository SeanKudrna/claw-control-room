# AGENTS.md — Claw Control Room Engineering Contract

This repository is production-facing (GitHub Pages). Prioritize maintainability, testability, and documentation discipline.

## Core standards

1) Code quality first
- Keep components/functions small and single-purpose.
- Prefer explicit typing and clear naming over clever shortcuts.
- Document non-obvious logic with comments/docstrings.

2) Modular architecture
- Frontend app lives in `src/` (React + TypeScript).
- Reusable browser logic belongs in `src/lib/` and hooks in `src/hooks/`.
- Reusable Python data/publish logic belongs in `scripts/lib/`.
- Keep script entrypoints thin.

3) Documentation is mandatory with behavior changes
Update these in the same change:
- `README.md`
- `handbook/ARCHITECTURE.md`
- `handbook/DEVELOPMENT.md`
- `CHANGELOG.md`

4) Quality gate before push
Run:
- `./scripts/quality_gate.sh`

(Checks Python compile/tests + React typecheck/build.)

5) No silent contract changes
If dashboard payload shape, timeline parsing, data-source behavior, or publish flow changes, document it in architecture/changelog.

## Repository layout

- `src/` — React + TypeScript UI
- `public/data/` — source/status config consumed by built app
- `docs/` — built static site artifact served by GitHub Pages
- `scripts/` — Python + shell automation tooling
- `scripts/lib/` — reusable Python modules
- `scripts/tests/` — Python tests
- `handbook/` — architecture/dev docs (source)

## Change style

- Prefer incremental, well-scoped commits.
- Keep backward compatibility unless there's a clear migration note.
- Keep status publishing commitless by default (gist backend) unless code/docs changed.
