#!/usr/bin/env python3
"""CLI wrapper for building dashboard status JSON."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure repository root is importable when running as a script.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.lib.status_builder import build_payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Build control-room status JSON")
    parser.add_argument("--workspace", default="/Users/seankudrna/.openclaw/workspace")
    parser.add_argument("--jobs-file", default="/Users/seankudrna/.openclaw/cron/jobs.json")
    parser.add_argument(
        "--out",
        default="/Users/seankudrna/.openclaw/workspace/claw-control-room/data/status.json",
    )
    args = parser.parse_args()

    payload = build_payload(Path(args.workspace), Path(args.jobs_file))

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
