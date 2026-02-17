# Development Guide

## Local dev

```bash
cd ~/.openclaw/workspace/claw-control-room
python3 scripts/build_status_json.py
open index.html
```

## Tests / quality gate

```bash
python3 -m py_compile scripts/build_status_json.py scripts/lib/status_builder.py scripts/tests/test_status_builder.py
python3 scripts/tests/test_status_builder.py
```

## Publish status only (no repo commit)

```bash
./scripts/publish_status.sh
```

## Publish code/docs

```bash
./scripts/update_and_push.sh
```

## Coding standards

- Keep reusable logic in `scripts/lib/`.
- Keep script entrypoints thin.
- Add/expand tests when changing parser/output logic.
- Update docs + changelog in the same change.

## Operational notes

- GitHub Pages serves from `main` branch root.
- `data/status.json` is cache-busted in browser via timestamp query param.
- If publish fails, check:
  - GitHub auth (`gh auth status`)
  - repo remote/branch
  - workflow cron payload logs
