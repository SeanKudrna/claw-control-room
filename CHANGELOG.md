# Changelog

## 2026-02-17

### Added
- Initial GitHub Pages dashboard scaffold (`index.html`, `app.js`, `styles.css`).
- Data builder CLI (`scripts/build_status_json.py`).
- Reusable builder module (`scripts/lib/status_builder.py`).
- Builder test suite (`scripts/tests/test_status_builder.py`).
- Engineering contract (`AGENTS.md`).
- Architecture and development docs (`docs/ARCHITECTURE.md`, `docs/DEVELOPMENT.md`).
- Gist-backed status publisher (`scripts/publish_status_gist.py`, `scripts/publish_status.sh`) to avoid commit spam for status refreshes.
- Status source config (`data/source.json`) and gist id registry (`.gist_id`).

### Changed
- `app.js` now resolves status from gist source config and falls back to local `data/status.json`.
- `scripts/update_and_push.sh` now focuses on code/docs publish path with quality gates.
- Dashboard data generation refactored from monolithic script logic to modular library.

### Ops
- GitHub Pages enabled for `SeanKudrna/claw-control-room`.
- Auto-refresh publishing configured via OpenClaw cron using gist backend (no repo commit per refresh).
