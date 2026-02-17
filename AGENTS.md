# AGENTS.md — Claw Control Room Engineering Contract

This repository is production-facing (GitHub Pages). Prioritize clarity, safety, and maintainability over speed hacks.

## Non-negotiables

1) **Code quality first**
- Keep functions small and single-purpose.
- Prefer explicit naming and typed/structured data over clever shortcuts.
- Include comments/docstrings for non-obvious logic.

2) **Modular architecture**
- Reusable logic belongs in `scripts/lib/`.
- CLI wrappers stay thin in `scripts/`.
- UI stays static/minimal (`index.html`, `app.js`, `styles.css`) and data-driven via `data/status.json`.

3) **Documentation must be updated with code changes**
When behavior/structure changes, update all relevant docs in the same change:
- `README.md`
- `docs/ARCHITECTURE.md`
- `docs/DEVELOPMENT.md`
- `CHANGELOG.md`

4) **Quality gates before publish**
Before pushing dashboard updates:
- `python3 -m py_compile ...`
- `python3 scripts/tests/test_status_builder.py`
- `python3 scripts/build_status_json.py`

5) **No silent breaking changes**
If an output contract changes (`data/status.json` shape, timeline parsing, job mapping), document it and call it out in changelog.

## Repository layout

- `index.html`, `app.js`, `styles.css` — static UI
- `data/status.json` — generated dashboard snapshot
- `scripts/build_status_json.py` — build entrypoint
- `scripts/lib/status_builder.py` — reusable data assembly logic
- `scripts/tests/` — lightweight tests
- `docs/` — architecture/dev/runbook docs

## Change style

- Prefer incremental refactors with clear intent.
- Keep commits scoped and readable.
- Maintain backward compatibility unless there is a clear reason not to.
