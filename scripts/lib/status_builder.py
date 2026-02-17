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
HEADING_RE = re.compile(r"^##\s+(.+)$")
HEADING_TIME_RE = re.compile(r"^(\d{1,2}:\d{2})")

CONTROL_ROOM_ROOT = Path(__file__).resolve().parents[2]


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


def parse_section_bullets(markdown: str, section_name: str) -> List[str]:
    """Return top-level bullet lines for a markdown `## <section_name>` section."""
    in_section = False
    bullets: List[str] = []

    for raw in markdown.splitlines():
        line = raw.strip()

        heading_match = HEADING_RE.match(line)
        if heading_match:
            heading = heading_match.group(1).strip().lower()
            in_section = heading == section_name.strip().lower()
            continue

        if not in_section:
            continue

        if line.startswith("## "):
            break

        if line.startswith("- "):
            text = line[2:].strip()
            if text:
                bullets.append(text)

    return bullets


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


def parse_workstream(today_status_markdown: str, timeline: List[Dict[str, str]], active_work: str) -> Dict[str, List[str]]:
    """Assemble now/next/done swimlanes from TODAY_STATUS with safe fallbacks."""
    now_lane = [active_work] if active_work else parse_section_bullets(today_status_markdown, "Now")
    next_lane = parse_section_bullets(today_status_markdown, "Next 3 meaningful blocks")
    done_lane = parse_section_bullets(today_status_markdown, "Last completed with proof")

    # Fallbacks when TODAY_STATUS is stale/missing.
    if not now_lane and timeline:
        now_lane = [timeline[0]["task"]]
    if not next_lane and timeline:
        next_lane = [block["task"] for block in timeline[1:4]]

    return {
        "now": now_lane[:3],
        "next": next_lane[:5],
        "done": done_lane[:5],
    }


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


def infer_activity_category(text: str) -> str:
    lowered = text.lower()
    if any(word in lowered for word in ["react", "typescript", "dashboard", "ui", "vite"]):
        return "ui"
    if any(word in lowered for word in ["watchdog", "reliability", "self-heal", "failover", "cron"]):
        return "reliability"
    if any(word in lowered for word in ["release", "tag", "version", "changelog"]):
        return "release"
    if any(word in lowered for word in ["doc", "architecture", "readme", "agends.md", "agents.md"]):
        return "docs"
    return "ops"


def recent_activity(memory_markdown: str, limit: int = 24) -> List[Dict[str, str]]:
    """Build a lightweight activity feed from today's memory bullets."""
    activities: List[Dict[str, str]] = []
    current_heading = ""
    current_time = ""

    for raw in memory_markdown.splitlines():
        line = raw.strip()

        if line.startswith("## "):
            current_heading = line[3:].strip()
            match = HEADING_TIME_RE.match(current_heading)
            current_time = match.group(1) if match else ""
            continue

        if not line.startswith("- "):
            continue

        text = line[2:].strip()
        if not text:
            continue

        category = infer_activity_category(f"{current_heading} {text}")
        activities.append(
            {
                "time": current_time or "n/a",
                "category": category,
                "text": text,
            }
        )

    return activities[-limit:]


def status_score(status: str) -> float:
    normalized = (status or "unknown").lower()
    if normalized in {"ok", "green", "success"}:
        return 1.0
    if normalized in {"yellow", "warn", "warning"}:
        return 0.55
    if normalized in {"error", "red", "failed"}:
        return 0.0
    return 0.35


def job_success_trend(jobs_file: Path, limit: int = 14) -> List[Dict[str, Any]]:
    """Build a recent run-quality trend from job last-run statuses."""
    content = read_text(jobs_file)
    if not content:
        return []

    try:
        doc = json.loads(content)
    except json.JSONDecodeError:
        return []

    points: List[Dict[str, Any]] = []
    for job in doc.get("jobs", []):
        if not job.get("enabled"):
            continue

        state = job.get("state", {})
        last_run_ms = state.get("lastRunAtMs")
        if not isinstance(last_run_ms, int):
            continue

        status = (state.get("lastStatus") or "unknown").lower()
        label = (
            dt.datetime.fromtimestamp(last_run_ms / 1000, dt.timezone.utc)
            .astimezone()
            .strftime("%H:%M")
        )
        points.append(
            {
                "label": label,
                "status": status,
                "score": status_score(status),
                "job": job.get("name", ""),
                "ts": last_run_ms,
            }
        )

    points.sort(key=lambda item: item.get("ts", 0))
    trimmed = points[-limit:]
    for point in trimmed:
        point.pop("ts", None)
    return trimmed


def reliability_trend(log_file: Path, limit: int = 14) -> List[Dict[str, Any]]:
    """Build reliability trend points from watchdog JSONL logs."""
    if not log_file.exists():
        return []

    points: List[Dict[str, Any]] = []
    for raw in log_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue

        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue

        ts = row.get("ts")
        if not isinstance(ts, int):
            continue

        status = (
            row.get("postHealth", {}).get("status")
            or row.get("health", {}).get("status")
            or ("yellow" if row.get("guardrailTriggered") else "green")
        )

        label = (
            dt.datetime.fromtimestamp(ts / 1000, dt.timezone.utc)
            .astimezone()
            .strftime("%H:%M")
        )

        points.append(
            {
                "label": label,
                "status": str(status).lower(),
                "score": status_score(str(status)),
                "ts": ts,
            }
        )

    points.sort(key=lambda item: item.get("ts", 0))
    trimmed = points[-limit:]
    for point in trimmed:
        point.pop("ts", None)
    return trimmed


def control_room_version() -> str:
    """Read dashboard app version from package.json."""
    package_json = CONTROL_ROOM_ROOT / "package.json"
    if not package_json.exists():
        return "0.0.0"

    try:
        data = json.loads(package_json.read_text(encoding="utf-8"))
        return str(data.get("version", "0.0.0"))
    except Exception:
        return "0.0.0"


def build_payload(workspace_root: Path, jobs_file: Path) -> Dict[str, Any]:
    """Build the dashboard JSON payload from current workspace state."""
    now_local = dt.datetime.now()
    today_file = workspace_root / "memory" / f"{now_local.strftime('%Y-%m-%d')}.md"

    plan_text = read_text(workspace_root / "DAILY_PLAN.md")
    status_text = read_text(workspace_root / "TODAY_STATUS.md")
    memory_text = read_text(today_file)

    status_parts = parse_today_status(status_text)
    timeline = parse_daily_plan_blocks(plan_text)

    return {
        "generatedAt": dt.datetime.now(dt.timezone.utc).isoformat(),
        "generatedAtLocal": now_local.strftime("%Y-%m-%d %H:%M %Z"),
        "controlRoomVersion": control_room_version(),
        "currentFocus": status_parts.get("currentFocus", ""),
        "activeWork": status_parts.get("activeWork", ""),
        "reliability": reliability_status(workspace_root),
        "timeline": timeline,
        "nextJobs": next_jobs(jobs_file),
        "findings": recent_findings(memory_text),
        "workstream": parse_workstream(status_text, timeline, status_parts.get("activeWork", "")),
        "charts": {
            "jobSuccessTrend": job_success_trend(jobs_file),
            "reliabilityTrend": reliability_trend(Path("/Users/seankudrna/.openclaw/logs/reliability-watchdog.jsonl")),
        },
        "activity": recent_activity(memory_text),
    }
