#!/usr/bin/env bash
set -euo pipefail

# Python pipeline checks
python3 -m py_compile \
  scripts/build_status_json.py \
  scripts/extract_release_notes.py \
  scripts/issue_snapshot.py \
  scripts/lib/status_builder.py \
  scripts/lib/runtime_events.py \
  scripts/lib/runtime_reconciler.py \
  scripts/mcp/jsonrpc_stdio.py \
  scripts/mcp/control_room_mcp_server.py \
  scripts/mcp/skill_lab_mcp_server.py \
  scripts/mcp/run_control_room_mcp_flow.py \
  scripts/runtime/collect_runtime_events.py \
  scripts/runtime/materialize_runtime_state.py \
  scripts/tests/test_extract_release_notes.py \
  scripts/tests/test_issue_snapshot.py \
  scripts/tests/test_status_builder.py \
  scripts/tests/test_runtime_reconciler.py \
  scripts/tests/test_runtime_materializer.py \
  scripts/tests/test_runtime_truth_stress.py \
  scripts/tests/test_control_room_mcp_flow.py \
  scripts/tests/test_collapsible_heading_compact.py

python3 scripts/tests/test_extract_release_notes.py
python3 scripts/tests/test_issue_snapshot.py
python3 scripts/tests/test_status_builder.py
python3 scripts/tests/test_runtime_reconciler.py
python3 scripts/tests/test_runtime_materializer.py
python3 scripts/tests/test_runtime_truth_stress.py
python3 scripts/tests/test_control_room_mcp_flow.py
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
node scripts/tests/test_runtime_job_details_modal.mjs
node scripts/tests/test_skill_actions_flow.mjs
kill ${PREVIEW_PID} >/dev/null 2>&1 || true
trap - EXIT

echo "Quality gate passed"
