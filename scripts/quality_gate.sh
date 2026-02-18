#!/usr/bin/env bash
set -euo pipefail

# Python pipeline checks
python3 -m py_compile \
  scripts/build_status_json.py \
  scripts/extract_release_notes.py \
  scripts/issue_snapshot.py \
  scripts/lib/status_builder.py \
  scripts/tests/test_extract_release_notes.py \
  scripts/tests/test_issue_snapshot.py \
  scripts/tests/test_status_builder.py \
  scripts/tests/test_collapsible_heading_compact.py

python3 scripts/tests/test_extract_release_notes.py
python3 scripts/tests/test_issue_snapshot.py
python3 scripts/tests/test_status_builder.py
python3 scripts/tests/test_collapsible_heading_compact.py
python3 scripts/build_status_json.py > /dev/null

# Frontend checks
if [[ ! -d node_modules ]]; then
  npm install --silent
fi

npm run typecheck
npm run build

# UI regression/readability guard
npm run preview -- --host 127.0.0.1 --port 4173 > /tmp/claw-control-room-preview.log 2>&1 &
PREVIEW_PID=$!
trap 'kill ${PREVIEW_PID} >/dev/null 2>&1 || true' EXIT

for _ in {1..20}; do
  if curl -fsS "http://127.0.0.1:4173/claw-control-room/" >/dev/null 2>&1; then
    break
  fi

  if ! kill -0 "${PREVIEW_PID}" >/dev/null 2>&1; then
    echo "Preview server exited unexpectedly" >&2
    cat /tmp/claw-control-room-preview.log >&2 || true
    exit 1
  fi

  sleep 0.5
done

if ! curl -fsS "http://127.0.0.1:4173/claw-control-room/" >/dev/null 2>&1; then
  echo "Preview server did not become ready in time" >&2
  cat /tmp/claw-control-room-preview.log >&2 || true
  exit 1
fi

node scripts/tests/test_ui_regressions.mjs
kill ${PREVIEW_PID} >/dev/null 2>&1 || true
trap - EXIT

echo "Quality gate passed"
