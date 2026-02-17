#!/usr/bin/env bash
set -euo pipefail

python3 -m py_compile \
  scripts/build_status_json.py \
  scripts/lib/status_builder.py \
  scripts/tests/test_status_builder.py

python3 scripts/tests/test_status_builder.py
python3 scripts/build_status_json.py > /dev/null

echo "Quality gate passed"
