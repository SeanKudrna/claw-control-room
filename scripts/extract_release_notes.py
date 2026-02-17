#!/usr/bin/env python3
"""Extract a single version section from CHANGELOG.md."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


VERSION_HEADING_RE = re.compile(r"^##\s+v?(\d+\.\d+\.\d+)\b")


def extract_release_notes(changelog_text: str, version: str) -> str:
    lines = changelog_text.splitlines()
    capture = False
    out: list[str] = []

    for line in lines:
        heading_match = VERSION_HEADING_RE.match(line.strip())
        if heading_match:
            heading_version = heading_match.group(1)
            if capture:
                break
            if heading_version == version:
                capture = True
                out.append(line)
                continue

        if capture:
            out.append(line)

    if not out:
        raise ValueError(f"Version {version} not found in changelog")

    return "\n".join(out).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract release notes for a version from CHANGELOG.md")
    parser.add_argument("--version", required=True, help="Semver string like 1.0.0")
    parser.add_argument("--changelog", default="CHANGELOG.md")
    args = parser.parse_args()

    changelog = Path(args.changelog)
    text = changelog.read_text(encoding="utf-8")
    notes = extract_release_notes(text, args.version)
    print(notes, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
