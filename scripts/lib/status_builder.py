#!/usr/bin/env python3
"""Builders for Claw Control Room status payloads.

This module is intentionally pure/side-effect-light so it can be reused by:
- local one-shot builds
- cron-based publish jobs
- future API/server variants
"""

from __future__ import annotations

import datetime as dt
import json
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List

BLOCK_RE = re.compile(r"^###\s+(\d{1,2}:\d{2})-(\d{1,2}:\d{2})\s+—\s+(.+)$")


def read_text(path: Path) -> str:
    """Return file text or empty string when missing."""
    return path.read_text(encoding="utf-8") if path.exists() else ""


def parse_daily_plan_blocks(plan_markdown: str) -> List[Dict[str, str]]:
    """Extract timeline blocks from DAILY_PLAN markdown."""
    timeline: List[Dict[str, str]] = []
    for line in plan_markdown.splitlines():
        match = BLOCK_RE.match(line.strip())
        if not match:
            continue
        timeline.append({"time": f"{match.group(1)}-{match.group(2)}", "task": match.group(3)})
    return timeline


def parse_today_status(today_status_markdown: str) -> Dict[str, str]:
    """Extract primary focus and active work from TODAY_STATUS markdown."""
    current_focus = ""
    active_work = ""

    for raw in today_status_markdown.splitlines():
        line = raw.strip()
        if line.startswith("- Primary focus:"):
            current_focus = line.replace("- Primary focus:", "").strip()
        elif line.startswith("- Running now:"):
            active_work = line.replace("- Running now:", "").strip()

    return {"currentFocus": current_focus, "activeWork": active_work}


def reliability_status(workspace_root: Path, window_hours: float = 8.0) -> Dict[str, str]:
    """Query watchdog report script for health status.

    Returns a compact shape for dashboard consumption.
    """
    script = workspace_root / "scripts" / "reliability_watchdog_report.py"
    if not script.exists():
        return {"status": "unknown"}

    try:
        output = subprocess.check_output(
            ["python3", str(script), "--window-hours", str(window_hours), "--json"],
            text=True,
            timeout=30,
        )
        report = json.loads(output)
        return {"status": report.get("health", {}).get("status", "unknown")}
    except Exception:
        return {"status": "unknown"}


def next_jobs(jobs_file: Path, limit: int = 8) -> List[Dict[str, Any]]:
    """Return the next enabled jobs sorted by next run timestamp."""
    content = read_text(jobs_file)
    if not content:
        return []

    try:
        doc = json.loads(content)
    except json.JSONDecodeError:
        return []

    jobs = [job for job in doc.get("jobs", []) if job.get("enabled")]
    jobs.sort(key=lambda job: job.get("state", {}).get("nextRunAtMs") or 2**63)

    out: List[Dict[str, Any]] = []
    for job in jobs[:limit]:
        next_run_ms = job.get("state", {}).get("nextRunAtMs")
        if isinstance(next_run_ms, int):
            next_run = (
                dt.datetime.fromtimestamp(next_run_ms / 1000, dt.timezone.utc)
                .astimezone()
                .strftime("%H:%M")
            )
        else:
            next_run = "n/a"

        out.append(
            {
                "name": job.get("name", ""),
                "nextRun": next_run,
                "lastStatus": job.get("state", {}).get("lastStatus"),
            }
        )

    return out


def recent_findings(memory_markdown: str, limit: int = 6) -> List[str]:
    """Take the last bullet-like memory lines as concise findings."""
    bullets = [line.strip() for line in memory_markdown.splitlines() if line.strip().startswith("-")]
    return [line.lstrip("- ") for line in bullets[-limit:]]


def build_payload(workspace_root: Path, jobs_file: Path) -> Dict[str, Any]:
    """Build the dashboard JSON payload from current workspace state."""
    now_local = dt.datetime.now()
    today_file = workspace_root / "memory" / f"{now_local.strftime('%Y-%m-%d')}.md"

    plan_text = read_text(workspace_root / "DAILY_PLAN.md")
    status_text = read_text(workspace_root / "TODAY_STATUS.md")
    memory_text = read_text(today_file)

    status_parts = parse_today_status(status_text)

    return {
        "generatedAt": dt.datetime.now(dt.timezone.utc).isoformat(),
        "generatedAtLocal": now_local.strftime("%Y-%m-%d %H:%M %Z"),
        "currentFocus": status_parts.get("currentFocus", ""),
        "activeWork": status_parts.get("activeWork", ""),
        "reliability": reliability_status(workspace_root),
        "timeline": parse_daily_plan_blocks(plan_text),
        "nextJobs": next_jobs(jobs_file),
        "findings": recent_findings(memory_text),
    }
