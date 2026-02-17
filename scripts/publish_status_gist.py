#!/usr/bin/env python3
"""Publish dashboard status payload to a GitHub Gist (no repo commit required)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.lib.status_builder import build_payload


def run_gh_api(path: str, method: str = "GET", payload: dict | None = None) -> dict:
    cmd = ["gh", "api", path]
    if method != "GET":
        cmd.extend(["-X", method])

    tmp_path = None
    if payload is not None:
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json") as tmp:
            json.dump(payload, tmp)
            tmp_path = tmp.name
        cmd.extend(["--input", tmp_path])

    try:
        output = subprocess.check_output(cmd, text=True)
        return json.loads(output)
    finally:
        if tmp_path:
            Path(tmp_path).unlink(missing_ok=True)


def resolve_gist_id(explicit: str | None, gist_id_file: Path) -> str:
    if explicit:
        return explicit.strip()
    if gist_id_file.exists():
        value = gist_id_file.read_text(encoding="utf-8").strip()
        if value:
            return value
    raise SystemExit(
        f"No gist id found. Pass --gist-id or create {gist_id_file} with the gist id."
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish control-room status payload to GitHub Gist")
    parser.add_argument("--workspace", default="/Users/seankudrna/.openclaw/workspace")
    parser.add_argument("--jobs-file", default="/Users/seankudrna/.openclaw/cron/jobs.json")
    parser.add_argument("--gist-id", default=None)
    parser.add_argument("--gist-id-file", default=str(ROOT / ".gist_id"))
    parser.add_argument("--filename", default="claw-control-room-status.json")
    args = parser.parse_args()

    workspace = Path(args.workspace)
    jobs_file = Path(args.jobs_file)
    gist_id = resolve_gist_id(args.gist_id, Path(args.gist_id_file))

    payload = build_payload(workspace, jobs_file)
    content = json.dumps(payload, indent=2) + "\n"

    patch_body = {
        "files": {
            args.filename: {
                "content": content,
            }
        }
    }
    updated = run_gh_api(f"gists/{gist_id}", method="PATCH", payload=patch_body)

    file_info = updated.get("files", {}).get(args.filename, {})
    raw_url = file_info.get("raw_url") or f"https://gist.githubusercontent.com/SeanKudrna/{gist_id}/raw/{args.filename}"

    print(json.dumps({
        "ok": True,
        "gistId": gist_id,
        "filename": args.filename,
        "rawUrl": raw_url,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
