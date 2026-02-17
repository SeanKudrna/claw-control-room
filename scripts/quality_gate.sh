#!/usr/bin/env bash
set -euo pipefail

# Python pipeline checks
python3 -m py_compile \
  scripts/build_status_json.py \
  scripts/lib/status_builder.py \
  scripts/tests/test_status_builder.py

python3 scripts/tests/test_status_builder.py
python3 scripts/build_status_json.py > /dev/null

# Frontend checks
if [[ ! -d node_modules ]]; then
  npm install --silent
fi

npm run typecheck
npm run build

echo "Quality gate passed"
