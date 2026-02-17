#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR"

usage() {
  cat <<EOF
Usage:
  ./scripts/update_and_push.sh --version <x.y.z> [--message "commit message"]

Behavior:
  1) bump package version (package.json + package-lock.json)
  2) run full quality gate
  3) commit + push changes
  4) create git tag v<version> and push tag
  5) create GitHub release with notes pulled from CHANGELOG.md section for that version
EOF
}

VERSION=""
MSG=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --version)
      VERSION="${2:-}"
      shift 2
      ;;
    --message)
      MSG="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown arg: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ -z "$VERSION" ]]; then
  echo "Error: --version is required" >&2
  usage
  exit 1
fi

if [[ ! "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "Error: version must be semver like 1.0.0" >&2
  exit 1
fi

TAG="v$VERSION"
MSG="${MSG:-release: $TAG}"

if git rev-parse "$TAG" >/dev/null 2>&1; then
  echo "Error: local tag $TAG already exists" >&2
  exit 1
fi

if git ls-remote --tags origin "refs/tags/$TAG" | grep -q .; then
  echo "Error: remote tag $TAG already exists" >&2
  exit 1
fi

# Keep app version authoritative in package manifests.
npm version "$VERSION" --no-git-tag-version >/dev/null

# Run full quality gate after version bump.
./scripts/quality_gate.sh

git add .
if git diff --cached --quiet; then
  echo "No code/doc/version changes to push"
  exit 0
fi

git commit -m "$MSG"
git push

git tag -a "$TAG" -m "Release $TAG"
git push origin "$TAG"

NOTES_FILE="$(mktemp)"
trap 'rm -f "$NOTES_FILE"' EXIT
python3 scripts/extract_release_notes.py --version "$VERSION" --changelog CHANGELOG.md > "$NOTES_FILE"

gh release create "$TAG" --title "$TAG" --notes-file "$NOTES_FILE"

echo "Release complete: $TAG"
