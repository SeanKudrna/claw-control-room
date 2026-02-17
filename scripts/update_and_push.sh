#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR"

MSG="${1:-dashboard: code/docs update $(date '+%Y-%m-%d %H:%M')}"

# Run full quality gate (includes React typecheck/build + Python checks)
./scripts/quality_gate.sh

git add .
if git diff --cached --quiet; then
  echo "No code/doc changes to push"
  exit 0
fi

git commit -m "$MSG"
git push

echo "Code/docs pushed"
