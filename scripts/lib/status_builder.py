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
from typing import Any, Dict, List, Optional, Tuple

BLOCK_RE = re.compile(r"^###\s+(\d{1,2}:\d{2})-(\d{1,2}:\d{2})\s+—\s+(.+)$")
HEADING_RE = re.compile(r"^##\s+(.+)$")
HEADING_TIME_RE = re.compile(r"^(\d{1,2}:\d{2})")
TIME_RANGE_RE = re.compile(r"(\d{1,2}:\d{2})-(\d{1,2}:\d{2})")
WORD_RE = re.compile(r"[a-z0-9]+")

SEMANTIC_STOPWORDS = {
    "a",
    "an",
    "and",
    "at",
    "by",
    "for",
    "from",
    "in",
    "into",
    "of",
    "on",
    "over",
    "the",
    "to",
    "under",
    "via",
    "with",
}

NEXT_LANE_DEDUPE_TIME_GRACE_MINUTES = 5
NEXT_LANE_DEDUPE_SIMILARITY_THRESHOLD = 0.6
NEXT_LANE_DEDUPE_STRONG_THRESHOLD = 0.85
NEXT_LANE_DEDUPE_MIN_TOKEN_OVERLAP = 2
NEXT_LANE_DEDUPE_OVERLAP_RATIO_THRESHOLD = 0.3

CONTROL_ROOM_ROOT = Path(__file__).resolve().parents[2]
SESSIONS_STORE_PATH = Path("/Users/seankudrna/.openclaw/agents/main/sessions/sessions.json")
CRON_RUNS_DIR = Path("/Users/seankudrna/.openclaw/cron/runs")
CRON_RUN_SESSION_KEY_RE = re.compile(r"^agent:main:cron:([^:]+):run:([^:]+)$")
EXCLUDED_RUNTIME_JOB_NAME_SUBSTRINGS = (
    "control room status publish",
)


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


def parse_hhmm_to_minutes(value: str) -> Optional[int]:
    try:
        hour_str, minute_str = value.split(":", 1)
        hour = int(hour_str)
        minute = int(minute_str)
    except ValueError:
        return None

    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        return None
    return hour * 60 + minute


def parse_time_range(value: str) -> Optional[Tuple[int, int]]:
    match = TIME_RANGE_RE.search(value)
    if not match:
        return None

    start = parse_hhmm_to_minutes(match.group(1))
    end = parse_hhmm_to_minutes(match.group(2))
    if start is None or end is None:
        return None
    return start, end


def normalize_semantic_text(value: str) -> str:
    """Normalize text for semantic comparison by stripping time ranges and punctuation."""
    cleaned = TIME_RANGE_RE.sub(" ", value)
    tokens = WORD_RE.findall(cleaned.lower())
    return " ".join(tokens)


def semantic_tokens(value: str) -> set[str]:
    """Return normalized semantic tokens, excluding stopwords."""
    cleaned = TIME_RANGE_RE.sub(" ", value)
    tokens = WORD_RE.findall(cleaned.lower())
    return {token for token in tokens if token not in SEMANTIC_STOPWORDS}


def semantic_similarity(tokens_a: set[str], tokens_b: set[str]) -> float:
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = len(tokens_a & tokens_b)
    union = len(tokens_a | tokens_b)
    return intersection / union if union else 0.0


def token_overlap_ratio(tokens_a: set[str], tokens_b: set[str]) -> float:
    if not tokens_a or not tokens_b:
        return 0.0
    overlap = len(tokens_a & tokens_b)
    return overlap / min(len(tokens_a), len(tokens_b))


def has_meaningful_token_overlap(tokens_a: set[str], tokens_b: set[str]) -> bool:
    overlap = len(tokens_a & tokens_b)
    if overlap < NEXT_LANE_DEDUPE_MIN_TOKEN_OVERLAP:
        return False
    return token_overlap_ratio(tokens_a, tokens_b) >= NEXT_LANE_DEDUPE_OVERLAP_RATIO_THRESHOLD


def time_ranges_overlap_or_close(
    range_a: Tuple[int, int],
    range_b: Tuple[int, int],
    grace_minutes: int = NEXT_LANE_DEDUPE_TIME_GRACE_MINUTES,
) -> bool:
    """Return True when ranges overlap or sit within grace minutes."""
    return range_a[0] <= range_b[1] + grace_minutes and range_b[0] <= range_a[1] + grace_minutes


def build_next_lane_meta(item: str) -> Dict[str, Any]:
    return {
        "text": item,
        "range": parse_time_range(item),
        "normalized": normalize_semantic_text(item),
        "tokens": semantic_tokens(item),
    }


def is_semantic_match(
    candidate: Dict[str, Any],
    existing: Dict[str, Any],
    threshold: float,
) -> bool:
    if candidate["normalized"] and candidate["normalized"] == existing["normalized"]:
        return True

    tokens_a = candidate["tokens"]
    tokens_b = existing["tokens"]
    if len(tokens_a) < 2 or len(tokens_b) < 2:
        return False

    similarity = semantic_similarity(tokens_a, tokens_b)
    if similarity >= threshold:
        return True

    overlap = tokens_a & tokens_b
    if len(overlap) >= NEXT_LANE_DEDUPE_MIN_TOKEN_OVERLAP:
        return tokens_a.issubset(tokens_b) or tokens_b.issubset(tokens_a)
    return False


def is_duplicate_next_item(candidate: Dict[str, Any], existing_items: List[Dict[str, Any]]) -> bool:
    """Return True when candidate duplicates any canonical next item."""
    for existing in existing_items:
        if candidate["normalized"] and candidate["normalized"] == existing["normalized"]:
            return True

        range_a = candidate.get("range")
        range_b = existing.get("range")
        if range_a and range_b:
            if not time_ranges_overlap_or_close(range_a, range_b):
                continue
            if is_semantic_match(candidate, existing, NEXT_LANE_DEDUPE_SIMILARITY_THRESHOLD):
                return True
            if has_meaningful_token_overlap(candidate["tokens"], existing["tokens"]):
                return True
            continue

        if is_semantic_match(candidate, existing, NEXT_LANE_DEDUPE_STRONG_THRESHOLD):
            return True

    return False


def dedupe_next_lane(timeline_items: List[str], status_items: List[str]) -> List[str]:
    """Return next-lane items with timeline entries canonicalized."""
    canonical_meta = [build_next_lane_meta(item) for item in timeline_items]
    deduped = list(timeline_items)
    seen_meta = list(canonical_meta)

    for item in status_items:
        meta = build_next_lane_meta(item)
        if is_duplicate_next_item(meta, seen_meta):
            continue
        deduped.append(item)
        seen_meta.append(meta)

    return deduped


def normalize_items(items: List[str], limit: int) -> List[str]:
    seen: set[str] = set()
    out: List[str] = []
    for item in items:
        text = item.strip()
        if not text:
            continue
        if text in seen:
            continue
        seen.add(text)
        out.append(text)
        if len(out) >= limit:
            break
    return out


def format_block(block: Dict[str, str]) -> str:
    return f"{block.get('time', 'n/a')} — {block.get('task', '').strip()}".strip()


def timeline_context(timeline: List[Dict[str, str]], now_local: dt.datetime) -> Dict[str, Any]:
    """Return timeline slices around `now_local` (current, next, completed)."""
    now_minutes = now_local.hour * 60 + now_local.minute

    normalized: List[Dict[str, Any]] = []
    for block in timeline:
        block_time = block.get("time", "")
        parsed = parse_time_range(block_time)
        if parsed is None:
            continue
        normalized.append(
            {
                "time": block_time,
                "task": block.get("task", ""),
                "start": parsed[0],
                "end": parsed[1],
            }
        )

    current: Optional[Dict[str, Any]] = None
    next_blocks: List[Dict[str, Any]] = []
    completed: List[Dict[str, Any]] = []

    for block in normalized:
        if block["start"] <= now_minutes < block["end"]:
            current = block
        elif now_minutes < block["start"]:
            next_blocks.append(block)
        elif block["end"] <= now_minutes:
            completed.append(block)

    if current is None and not next_blocks and normalized:
        # Past the final planned block for the day.
        completed = normalized

    return {
        "current": current,
        "next": next_blocks,
        "completed": completed,
    }


def is_stale_active_work(active_work: str, now_local: dt.datetime, grace_minutes: int = 10) -> bool:
    parsed = parse_time_range(active_work)
    if parsed is None:
        return False

    _, end = parsed
    now_minutes = now_local.hour * 60 + now_local.minute
    return now_minutes > (end + grace_minutes)


def resolve_active_work(
    raw_active_work: str,
    timeline: List[Dict[str, str]],
    now_local: dt.datetime,
) -> str:
    """Resolve active work with stale guard + timeline fallback."""
    context = timeline_context(timeline, now_local)

    if raw_active_work and not is_stale_active_work(raw_active_work, now_local):
        return raw_active_work

    current = context.get("current")
    if current:
        return format_block(current)

    next_blocks = context.get("next") or []
    if next_blocks:
        return f"Next up: {format_block(next_blocks[0])}"

    return raw_active_work


def resolve_current_focus(raw_focus: str, active_work: str, timeline: List[Dict[str, str]], now_local: dt.datetime) -> str:
    """Resolve current focus with robust fallbacks when TODAY_STATUS is stale/incomplete."""
    normalized_focus = raw_focus.strip()
    if normalized_focus and normalized_focus.lower() not in {"n/a", "na", "none", "unknown"}:
        return normalized_focus

    context = timeline_context(timeline, now_local)
    current = context.get("current")
    if current and current.get("task"):
        return current["task"]

    if active_work:
        # If active_work includes a leading time-range, strip it for cleaner focus text.
        stripped = TIME_RANGE_RE.sub("", active_work, count=1).lstrip(" —-:")
        return stripped or active_work

    next_blocks = context.get("next") or []
    if next_blocks:
        return next_blocks[0].get("task", "")

    return "Reliability monitoring + scheduled execution"


def is_future_or_untimed(item: str, now_local: dt.datetime) -> bool:
    """Return True for future/no-time items, False for already-ended timed blocks."""
    parsed = parse_time_range(item)
    if parsed is None:
        return True

    _, end = parsed
    now_minutes = now_local.hour * 60 + now_local.minute
    return end > now_minutes


def parse_workstream(
    today_status_markdown: str,
    timeline: List[Dict[str, str]],
    active_work: str,
    now_local: dt.datetime,
) -> Dict[str, List[str]]:
    """Assemble now/next/done swimlanes from TODAY_STATUS with timeline-aware fallbacks."""
    context = timeline_context(timeline, now_local)
    current = context.get("current")
    next_blocks = context.get("next") or []
    completed = context.get("completed") or []

    now_lane: List[str] = []
    if current:
        now_lane.append(format_block(current))
    elif active_work:
        now_lane.append(active_work)
    else:
        now_lane.extend(parse_section_bullets(today_status_markdown, "Now"))

    timeline_next = [format_block(block) for block in next_blocks[:3]]
    status_next = [
        item
        for item in parse_section_bullets(today_status_markdown, "Next 3 meaningful blocks")
        if is_future_or_untimed(item, now_local)
    ]
    next_lane = dedupe_next_lane(timeline_next, status_next)

    done_lane = parse_section_bullets(today_status_markdown, "Last completed with proof")
    if not done_lane:
        done_lane.extend([f"Completed: {format_block(block)}" for block in completed[-3:]])

    return {
        "now": normalize_items(now_lane, limit=3),
        "next": normalize_items(next_lane, limit=5),
        "done": normalize_items(done_lane, limit=5),
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


def finished_run_session_ids(job_id: str, runs_dir: Path, cache: Dict[str, set[str]]) -> set[str]:
    """Return finished run session ids for a job from cron JSONL run history."""
    if job_id in cache:
        return cache[job_id]

    run_file = runs_dir / f"{job_id}.jsonl"
    if not run_file.exists():
        cache[job_id] = set()
        return cache[job_id]

    finished: set[str] = set()
    for raw in run_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue

        if row.get("action") != "finished":
            continue

        session_id = row.get("sessionId")
        if isinstance(session_id, str) and session_id:
            finished.add(session_id)

    cache[job_id] = finished
    return finished


def runtime_activity(
    jobs_file: Path,
    sessions_store_path: Path = SESSIONS_STORE_PATH,
    runs_dir: Path = CRON_RUNS_DIR,
    max_age_ms: int = 6 * 60 * 60 * 1000,
) -> Dict[str, Any]:
    """Return real-time runtime/idle state from cron run sessions.

    Detection model:
    - read run-session records from sessions store (`agent:main:cron:<jobId>:run:<sessionId>`)
    - reconcile against cron run logs (`runs/<jobId>.jsonl`) finished entries
    - sessions present but not finished are considered actively running

    This gives deterministic active-run visibility and timer start timestamps.
    """
    now_ms = int(dt.datetime.now(dt.timezone.utc).timestamp() * 1000)

    jobs_doc_text = read_text(jobs_file)
    jobs_by_id: Dict[str, str] = {}
    if jobs_doc_text:
        try:
            jobs_doc = json.loads(jobs_doc_text)
            jobs_by_id = {
                str(job.get("id")): str(job.get("name", ""))
                for job in jobs_doc.get("jobs", [])
                if job.get("id")
            }
        except json.JSONDecodeError:
            jobs_by_id = {}

    if not sessions_store_path.exists():
        return {
            "status": "idle",
            "isIdle": True,
            "activeCount": 0,
            "activeRuns": [],
            "checkedAtMs": now_ms,
            "source": "sessions-store-missing",
        }

    try:
        sessions_doc = json.loads(sessions_store_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {
            "status": "idle",
            "isIdle": True,
            "activeCount": 0,
            "activeRuns": [],
            "checkedAtMs": now_ms,
            "source": "sessions-store-invalid",
        }

    if not isinstance(sessions_doc, dict):
        return {
            "status": "idle",
            "isIdle": True,
            "activeCount": 0,
            "activeRuns": [],
            "checkedAtMs": now_ms,
            "source": "sessions-store-unexpected-shape",
        }

    finished_cache: Dict[str, set[str]] = {}
    active_runs: List[Dict[str, Any]] = []

    for key, meta in sessions_doc.items():
        if not isinstance(key, str) or not isinstance(meta, dict):
            continue

        match = CRON_RUN_SESSION_KEY_RE.match(key)
        if not match:
            continue

        job_id, session_id = match.groups()
        finished_ids = finished_run_session_ids(job_id, runs_dir, finished_cache)
        if session_id in finished_ids:
            continue

        started_at_ms = meta.get("updatedAt")
        if not isinstance(started_at_ms, int):
            continue

        running_for_ms = max(0, now_ms - started_at_ms)
        if running_for_ms > max_age_ms:
            # Ignore orphaned stale sessions to avoid false "running" flags.
            continue

        job_name = jobs_by_id.get(job_id, f"Unknown job ({job_id[:8]})")
        normalized_job_name = job_name.lower()
        if any(token in normalized_job_name for token in EXCLUDED_RUNTIME_JOB_NAME_SUBSTRINGS):
            # Prevent self-referential/sticky runtime false positives from fast publisher runs.
            continue

        started_local = (
            dt.datetime.fromtimestamp(started_at_ms / 1000, dt.timezone.utc)
            .astimezone()
            .strftime("%Y-%m-%d %H:%M:%S")
        )

        active_runs.append(
            {
                "jobId": job_id,
                "jobName": job_name,
                "sessionId": session_id,
                "startedAtMs": started_at_ms,
                "startedAtLocal": started_local,
                "runningForMs": running_for_ms,
            }
        )

    active_runs.sort(key=lambda item: item.get("startedAtMs", 0))

    return {
        "status": "running" if active_runs else "idle",
        "isIdle": len(active_runs) == 0,
        "activeCount": len(active_runs),
        "activeRuns": active_runs,
        "checkedAtMs": now_ms,
        "source": "session-store + cron-run-log reconciliation",
    }


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

    active_work = resolve_active_work(status_parts.get("activeWork", ""), timeline, now_local)
    current_focus = resolve_current_focus(status_parts.get("currentFocus", ""), active_work, timeline, now_local)

    return {
        "generatedAt": dt.datetime.now(dt.timezone.utc).isoformat(),
        "generatedAtLocal": now_local.strftime("%Y-%m-%d %H:%M %Z"),
        "controlRoomVersion": control_room_version(),
        "currentFocus": current_focus,
        "activeWork": active_work,
        "reliability": reliability_status(workspace_root),
        "timeline": timeline,
        "nextJobs": next_jobs(jobs_file),
        "findings": recent_findings(memory_text),
        "workstream": parse_workstream(status_text, timeline, active_work, now_local),
        "charts": {
            "jobSuccessTrend": job_success_trend(jobs_file),
            "reliabilityTrend": reliability_trend(Path("/Users/seankudrna/.openclaw/logs/reliability-watchdog.jsonl")),
        },
        "activity": recent_activity(memory_text),
        "runtime": runtime_activity(jobs_file),
    }
