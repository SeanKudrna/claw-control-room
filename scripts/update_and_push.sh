#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR"

# Quick quality gate before publishing.
python3 -m py_compile scripts/build_status_json.py scripts/lib/status_builder.py scripts/tests/test_status_builder.py
python3 scripts/tests/test_status_builder.py

# Build fresh dashboard data.
python3 scripts/build_status_json.py

git add data/status.json
if git diff --cached --quiet; then
  echo "No dashboard data changes"
  exit 0
fi

git commit -m "dashboard: update status $(date '+%Y-%m-%d %H:%M')"
git push

echo "Dashboard pushed"
