#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR"

python3 scripts/build_status_json.py

git add data/status.json
if git diff --cached --quiet; then
  echo "No dashboard data changes"
  exit 0
fi

git commit -m "dashboard: update status $(date '+%Y-%m-%d %H:%M')"
git push

echo "Dashboard pushed"
