#!/usr/bin/env python3
"""Create a markdown snapshot of open GitHub issues for control-room triage."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
from pathlib import Path
from typing import Any


def run_gh_issue_list(repo: str, limit: int) -> list[dict[str, Any]]:
    cmd = [
        "gh",
        "issue",
        "list",
        "--repo",
        repo,
        "--state",
        "open",
        "--limit",
        str(limit),
        "--json",
        "number,title,url,labels,createdAt,updatedAt,author",
    ]
    output = subprocess.check_output(cmd, text=True)
    return json.loads(output)


def render_markdown(repo: str, issues: list[dict[str, Any]]) -> str:
    now = dt.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
    lines: list[str] = []

    lines.append("# Control Room Issue Snapshot")
    lines.append("")
    lines.append(f"- Repo: `{repo}`")
    lines.append(f"- Generated: {now}")
    lines.append(f"- Open issues: {len(issues)}")
    lines.append("")

    if not issues:
        lines.append("No open issues right now. ✅")
        lines.append("")
        return "\n".join(lines)

    lines.append("## Open issues")
    lines.append("")

    for issue in issues:
        number = issue.get("number", "?")
        title = issue.get("title", "(no title)")
        url = issue.get("url", "")
        updated_at = issue.get("updatedAt", "")
        labels = [label.get("name", "") for label in issue.get("labels", []) if isinstance(label, dict)]
        labels_display = ", ".join(labels) if labels else "none"

        lines.append(f"### #{number} — {title}")
        lines.append(f"- URL: {url}")
        lines.append(f"- Labels: {labels_display}")
        lines.append(f"- Updated: {updated_at}")
        lines.append("")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate markdown snapshot of open GitHub issues")
    parser.add_argument("--repo", default="SeanKudrna/claw-control-room")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument(
        "--out",
        default="/Users/seankudrna/.openclaw/workspace/status/control-room-issues.md",
    )
    args = parser.parse_args()

    issues = run_gh_issue_list(args.repo, args.limit)
    markdown = render_markdown(args.repo, issues)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(markdown + "\n", encoding="utf-8")

    print(json.dumps({"ok": True, "openIssues": len(issues), "out": str(out_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
