# Changelog

## 2026-02-17

### Added
- Initial GitHub Pages dashboard scaffold (`index.html`, `app.js`, `styles.css`).
- Data builder CLI (`scripts/build_status_json.py`).
- Reusable builder module (`scripts/lib/status_builder.py`).
- Builder test suite (`scripts/tests/test_status_builder.py`).
- Engineering contract (`AGENTS.md`).
- Architecture and development docs (`docs/ARCHITECTURE.md`, `docs/DEVELOPMENT.md`).

### Changed
- `scripts/update_and_push.sh` now runs compile/test quality gates before publish.
- Dashboard data generation refactored from monolithic script logic to modular library.

### Ops
- GitHub Pages enabled for `SeanKudrna/claw-control-room`.
- Auto-refresh publishing configured via OpenClaw cron.
