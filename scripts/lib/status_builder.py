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
import os
import re
import subprocess
import hashlib
from collections import deque
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from scripts.lib.runtime_reconciler import normalize_run_key, reconcile

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
SUBAGENT_REGISTRY_PATH = Path("/Users/seankudrna/.openclaw/subagents/runs.json")
RUNTIME_STATE_FILE = Path("/Users/seankudrna/.openclaw/workspace/status/runtime-state.json")
CRON_RUN_SESSION_KEY_RE = re.compile(r"^agent:main:cron:([^:]+):run:([^:]+)$")
MAIN_SESSION_KEY = "agent:main:main"
RUNTIME_STALE_MS = 10 * 60 * 1000
RUNTIME_MATERIALIZED_MAX_AGE_MS = 90 * 1000
MAIN_SESSION_RUNTIME_MAX_AGE_MS = 2 * 60 * 1000
MAIN_SESSION_PENDING_CALL_MAX_AGE_MS = 10 * 60 * 1000
MAIN_SESSION_LOCK_STALE_MS = 30 * 60 * 1000
ACTIVE_WORK_SINGLE_TIME_STALE_MINUTES = 90
ACTIVE_WORK_COMPLETED_STALE_MINUTES = 15
ACTIVE_WORK_COMPLETION_TOKENS = (
    "complete",
    "completed",
    "done",
    "finished",
)
WORKSTREAM_DONE_MAX_AGE_MINUTES = 6 * 60
WORKSTREAM_NEXT_JOB_HORIZON_MINUTES = 2 * 60
WORKSTREAM_NEXT_JOB_PRIORITY_WINDOW_MINUTES = 90
WORKSTREAM_DONE_PROOF_PREFIXES = (
    "proof",
    "evidence",
    "command",
)
EXCLUDED_RUNTIME_JOB_NAME_SUBSTRINGS = (
    "control room status publish",
)
WORKSTREAM_STATE_FILE = Path("/Users/seankudrna/.openclaw/workspace/status/control-room-workstream-state.json")
CLAWPRIME_MEMORY_FILE = "ClawPrime_Memory.md"
SKILL_KEYWORDS: Dict[str, Tuple[str, ...]] = {
    "runtime-orchestration": ("runtime", "orchestration", "scheduler", "cron", "subagent", "queue"),
    "reliability-guardrails": ("reliability", "watchdog", "self-heal", "guardrail", "failover", "degraded"),
    "ui-systems": ("ui", "ux", "dashboard", "react", "mobile", "accessibility"),
    "release-operations": ("release", "tag", "version", "changelog", "publish", "quality gate"),
    "memory-evolution": ("memory", "evolution", "artifact", "learning", "pattern", "distilled"),
    "observability": ("trend", "signal", "telemetry", "monitor", "status", "source"),
}
SKILL_CATALOG: List[Dict[str, Any]] = [
    {
        "id": "runtime-orchestration",
        "name": "Runtime Orchestration",
        "description": "Coordinate cron and subagent execution lanes into one deterministic runtime view.",
        "effect": "Keeps now/next/done and runtime surfaces synchronized.",
        "dependencies": [],
    },
    {
        "id": "reliability-guardrails",
        "name": "Reliability Guardrails",
        "description": "Detect and surface degraded states with explicit fallback semantics.",
        "effect": "Improves trust by preventing silent failure modes.",
        "dependencies": ["runtime-orchestration"],
    },
    {
        "id": "ui-systems",
        "name": "UI Systems",
        "description": "Ship mobile-first, accessible dashboard interactions and visual hierarchy.",
        "effect": "Raises scanability and interaction quality across devices.",
        "dependencies": ["runtime-orchestration"],
    },
    {
        "id": "observability",
        "name": "Observability",
        "description": "Turn activity, trend, and source signals into operator-ready insight.",
        "effect": "Accelerates diagnosis and informed execution decisions.",
        "dependencies": ["runtime-orchestration"],
    },
    {
        "id": "release-operations",
        "name": "Release Operations",
        "description": "Run semver, quality gate, proof, and publish workflow consistently.",
        "effect": "Keeps delivery predictable with auditable release evidence.",
        "dependencies": ["reliability-guardrails", "observability"],
    },
    {
        "id": "memory-evolution",
        "name": "Memory Evolution",
        "description": "Extract durable patterns from memory artifacts and reinforce high-ROI behaviors.",
        "effect": "Compounds operational quality through deterministic learning loops.",
        "dependencies": ["reliability-guardrails", "ui-systems"],
    },
]

SKILL_TIER_FRAMEWORK: List[Dict[str, Any]] = [
    {
        "tier": 1,
        "title": "Foundation",
        "definition": "Establish baseline terminology and starter workflows for {domain}.",
        "difference": "Unlocks dependable baseline execution in this domain.",
    },
    {
        "tier": 2,
        "title": "Guided Delivery",
        "definition": "Deliver scoped improvements for {domain} with QA-guided feedback loops.",
        "difference": "Moves from familiarity to repeatable hands-on delivery.",
    },
    {
        "tier": 3,
        "title": "Independent Reliability",
        "definition": "Run {domain} workflows end-to-end with consistent reliability.",
        "difference": "Shifts from guided execution into autonomous ownership.",
    },
    {
        "tier": 4,
        "title": "Strategic Optimization",
        "definition": "Instrument and optimize {domain} systems proactively.",
        "difference": "Elevates delivery into durable system-level optimization.",
    },
    {
        "tier": 5,
        "title": "System Stewardship",
        "definition": "Set standards and evolve long-term capability across {domain}.",
        "difference": "Represents expert-level stewardship and long-range leverage.",
    },
]

SKILL_MAX_TIER = 5

WORKSTREAM_RUNTIME_NOW_LIMIT = 1
WORKSTREAM_NEXT_LIMIT = 5
WORKSTREAM_DONE_LIMIT = 5
DONE_LANE_TIME_RANGE_PREFIX_RE = re.compile(r"^\s*(\d{1,2}:\d{2})-(\d{1,2}:\d{2})\s*[—\-:]\s*(.+)$")
DONE_LANE_TIME_PREFIX_RE = re.compile(r"^\s*(\d{1,2}:\d{2})\s*[—\-:]\s*(.+)$")


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


def parse_leading_time_minutes(value: str) -> Optional[int]:
    match = HEADING_TIME_RE.match(value.strip())
    if not match:
        return None
    return parse_hhmm_to_minutes(match.group(1))


def format_minutes_hhmm(minutes: int) -> str:
    normalized = minutes % (24 * 60)
    return f"{normalized // 60:02d}:{normalized % 60:02d}"


def format_done_lane_item(item: str) -> str:
    """Prefix done-lane entries with completion time when derivable.

    Priority:
    - time ranges (`HH:MM-HH:MM`) use end-time as completion indicator
    - single leading time (`HH:MM`) uses that time
    - otherwise, keep item unchanged
    """
    text = item.strip()
    if not text:
        return text

    range_match = DONE_LANE_TIME_RANGE_PREFIX_RE.match(text)
    if range_match:
        end_minutes = parse_hhmm_to_minutes(range_match.group(2))
        if end_minutes is None:
            return text
        return f"{format_minutes_hhmm(end_minutes)} — {range_match.group(3).strip()}"

    time_match = DONE_LANE_TIME_PREFIX_RE.match(text)
    if time_match:
        leading_minutes = parse_hhmm_to_minutes(time_match.group(1))
        if leading_minutes is None:
            return text
        return f"{format_minutes_hhmm(leading_minutes)} — {time_match.group(2).strip()}"

    return text


def infer_time_anchor(item: str, now_local: dt.datetime) -> Optional[dt.datetime]:
    """Infer a local datetime anchor from a text item across common timestamp formats."""
    text = item.strip()
    if not text:
        return None

    iso_match = re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?(?:Z|[+-]\d{2}:?\d{2})?", text)
    if iso_match:
        parsed_ms = parse_timestamp_ms(iso_match.group(0))
        if parsed_ms is not None:
            return dt.datetime.fromtimestamp(parsed_ms / 1000, dt.timezone.utc).astimezone(now_local.tzinfo)

    dated_match = re.search(r"(\d{4}-\d{2}-\d{2})[ T](\d{1,2}:\d{2})", text)
    if dated_match:
        try:
            parsed = dt.datetime.fromisoformat(f"{dated_match.group(1)} {dated_match.group(2)}")
            return parsed.replace(tzinfo=now_local.tzinfo)
        except ValueError:
            pass

    parsed_range = parse_time_range(text)
    if parsed_range is not None:
        anchor_minutes = parsed_range[1]
    else:
        single_time = parse_leading_time_minutes(text)
        if single_time is None:
            return None
        anchor_minutes = single_time

    anchor = now_local.replace(hour=anchor_minutes // 60, minute=anchor_minutes % 60, second=0, microsecond=0)
    if anchor > now_local + dt.timedelta(hours=12):
        anchor -= dt.timedelta(days=1)
    return anchor


def is_done_item_fresh(item: str, now_local: dt.datetime, max_age_minutes: int = WORKSTREAM_DONE_MAX_AGE_MINUTES) -> bool:
    anchor = infer_time_anchor(item, now_local)
    if anchor is None:
        return True
    return (now_local - anchor) <= dt.timedelta(minutes=max_age_minutes)


def is_proof_scaffolding_line(item: str) -> bool:
    stripped = item.strip()
    if not stripped:
        return True

    lower = stripped.lower().strip(":")
    if any(lower.startswith(prefix) for prefix in WORKSTREAM_DONE_PROOF_PREFIXES):
        return True

    if stripped.startswith("`"):
        return True

    return False


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
    text = active_work.strip()
    if not text:
        return False

    now_minutes = now_local.hour * 60 + now_local.minute
    lowered = text.lower()
    has_completion_token = any(token in lowered for token in ACTIVE_WORK_COMPLETION_TOKENS)

    parsed = parse_time_range(text)
    if parsed is not None:
        _, end = parsed
        cutoff = ACTIVE_WORK_COMPLETED_STALE_MINUTES if has_completion_token else grace_minutes
        return now_minutes > (end + cutoff)

    single_time = parse_leading_time_minutes(text)
    if single_time is not None:
        if single_time > now_minutes:
            # A leading future time likely represents upcoming work.
            return False

        age_minutes = now_minutes - single_time
        cutoff = ACTIVE_WORK_COMPLETED_STALE_MINUTES if has_completion_token else ACTIVE_WORK_SINGLE_TIME_STALE_MINUTES
        return age_minutes > cutoff

    if has_completion_token:
        # "running now" should not be a completed item with no current-time context.
        return True

    return False


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


def has_time_hint(item: str) -> bool:
    return parse_time_range(item) is not None or parse_leading_time_minutes(item) is not None


def is_future_timed_item(item: str, now_local: dt.datetime) -> bool:
    """Return True only for timed items that are still upcoming."""
    now_minutes = now_local.hour * 60 + now_local.minute

    parsed = parse_time_range(item)
    if parsed is not None:
        _, end = parsed
        return end > now_minutes

    single_time = parse_leading_time_minutes(item)
    if single_time is None:
        return False

    return single_time > now_minutes


def timeline_events(timeline: List[Dict[str, str]], now_local: dt.datetime) -> List[Dict[str, Any]]:
    """Return timeline blocks that have not yet completed as unified events."""
    day_start = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    now_ms = int(now_local.timestamp() * 1000)
    events: List[Dict[str, Any]] = []

    for block in timeline:
        parsed = parse_time_range(block.get("time", ""))
        if parsed is None:
            continue
        start_minutes, end_minutes = parsed
        start_dt = day_start + dt.timedelta(minutes=start_minutes)
        end_dt = day_start + dt.timedelta(minutes=end_minutes)
        start_ms = int(start_dt.timestamp() * 1000)
        end_ms = int(end_dt.timestamp() * 1000)
        if end_ms <= now_ms:
            continue
        task = (block.get("task") or "").strip()
        time_label = block.get("time", "n/a")
        event_id = f"timeline:{start_dt.strftime('%Y-%m-%d')}:{time_label}:{task.lower()}"
        events.append(
            {
                "id": event_id,
                "kind": "timeline",
                "startMs": start_ms,
                "endMs": end_ms,
                "label": format_block(block),
            }
        )

    events.sort(key=lambda item: (item.get("startMs", 0), item.get("id", "")))
    return events


def scheduled_job_events(jobs_file: Path, now_local: dt.datetime) -> List[Dict[str, Any]]:
    """Return future scheduled cron runs as unified events."""
    content = read_text(jobs_file)
    if not content:
        return []

    try:
        doc = json.loads(content)
    except json.JSONDecodeError:
        return []

    now_ms = int(now_local.astimezone(dt.timezone.utc).timestamp() * 1000)
    events: List[Dict[str, Any]] = []

    for job in doc.get("jobs", []):
        if not isinstance(job, dict) or not job.get("enabled"):
            continue
        job_id = str(job.get("id") or "")
        name = str(job.get("name") or "Unnamed job").strip()
        next_run_ms = job.get("state", {}).get("nextRunAtMs")
        if not isinstance(next_run_ms, int) or next_run_ms < now_ms:
            continue
        local_label = dt.datetime.fromtimestamp(next_run_ms / 1000, dt.timezone.utc).astimezone(now_local.tzinfo).strftime("%H:%M")
        events.append(
            {
                "id": f"job:{job_id}:{next_run_ms}",
                "kind": "job",
                "startMs": next_run_ms,
                "label": f"{local_label} — Scheduled job: {name}",
            }
        )

    events.sort(key=lambda item: (item.get("startMs", 0), item.get("id", "")))
    return events


def runtime_events(runtime: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return active runtime rows as unified running events."""
    active_runs = runtime.get("activeRuns", []) if isinstance(runtime, dict) else []
    if not isinstance(active_runs, list):
        return []

    events: List[Dict[str, Any]] = []
    for row in active_runs:
        if not isinstance(row, dict):
            continue
        started_at_ms = row.get("startedAtMs")
        if not isinstance(started_at_ms, int):
            continue
        session_id = str(row.get("sessionId") or row.get("jobId") or row.get("runId") or "runtime")
        summary = str(row.get("summary") or row.get("jobName") or "Running activity").strip()
        events.append(
            {
                "id": f"runtime:{session_id}",
                "kind": "runtime",
                "startMs": started_at_ms,
                "label": summary,
            }
        )

    events.sort(key=lambda item: (item.get("startMs", 0), item.get("id", "")))
    return events


def load_workstream_state(state_path: Path, now_local: dt.datetime) -> Dict[str, Any]:
    today = now_local.strftime("%Y-%m-%d")
    default = {"day": today, "seenNow": [], "done": [], "labels": {}}
    if not state_path.exists():
        return default

    try:
        doc = json.loads(state_path.read_text(encoding="utf-8"))
    except Exception:
        return default

    if not isinstance(doc, dict) or doc.get("day") != today:
        return default

    seen_now = [value for value in doc.get("seenNow", []) if isinstance(value, str)]
    done = [value for value in doc.get("done", []) if isinstance(value, str)]
    labels_doc = doc.get("labels", {})
    labels = {
        key: value
        for key, value in labels_doc.items()
        if isinstance(labels_doc, dict) and isinstance(key, str) and isinstance(value, str)
    }
    return {"day": today, "seenNow": seen_now, "done": done, "labels": labels}


def save_workstream_state(state_path: Path, state: Dict[str, Any]) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def build_workstream_lanes(
    timeline: List[Dict[str, str]],
    jobs_file: Path,
    runtime: Dict[str, Any],
    now_local: dt.datetime,
    state_path: Path,
) -> Dict[str, List[str]]:
    """Build deterministic now/next/done lanes from unified event model."""
    future_events = timeline_events(timeline, now_local) + scheduled_job_events(jobs_file, now_local)
    future_events.sort(key=lambda item: (item.get("startMs", 0), item.get("id", "")))
    active_events = runtime_events(runtime)

    state = load_workstream_state(state_path, now_local)
    labels = dict(state.get("labels", {}))
    seen_now = set(state.get("seenNow", []))
    done_ids = [item for item in state.get("done", []) if isinstance(item, str)]

    now_events: List[Dict[str, Any]] = []
    next_events: List[Dict[str, Any]] = list(future_events)
    if active_events:
        now_events = active_events[:WORKSTREAM_RUNTIME_NOW_LIMIT]
    elif future_events:
        now_events = [future_events[0]]
        next_events = future_events[1:]

    now_ids = {event["id"] for event in now_events}
    future_ids = {event["id"] for event in future_events}

    for event in now_events + next_events + active_events:
        labels[event["id"]] = event["label"]

    seen_now.update(now_ids)

    transitioned_done = [
        event_id
        for event_id in state.get("seenNow", [])
        if event_id not in now_ids and event_id not in future_ids
    ]
    for event_id in transitioned_done:
        if event_id not in done_ids:
            done_ids.append(event_id)

    done_lane = [labels[event_id] for event_id in done_ids if event_id in labels]
    done_lane = list(reversed(done_lane))
    now_lane = [event["label"] for event in now_events]
    next_lane = [event["label"] for event in next_events]

    output = {
        "now": normalize_items(now_lane, limit=WORKSTREAM_RUNTIME_NOW_LIMIT),
        "next": normalize_items(next_lane, limit=WORKSTREAM_NEXT_LIMIT),
        "done": normalize_items(done_lane, limit=WORKSTREAM_DONE_LIMIT),
    }

    active_labels = set(output["now"])
    next_unique = [item for item in output["next"] if item not in active_labels]
    done_unique = [item for item in output["done"] if item not in active_labels and item not in set(next_unique)]
    output["next"] = next_unique
    output["done"] = done_unique

    persisted_done_ids = [event_id for event_id in done_ids if labels.get(event_id) in output["done"]]
    output["done"] = [format_done_lane_item(item) for item in output["done"]]
    new_state = {
        "day": now_local.strftime("%Y-%m-%d"),
        "seenNow": sorted(seen_now),
        "done": persisted_done_ids,
        "labels": labels,
    }
    save_workstream_state(state_path, new_state)
    return output


def parse_workstream(
    today_status_markdown: str,
    timeline: List[Dict[str, str]],
    active_work: str,
    now_local: dt.datetime,
    near_term_jobs: Optional[List[str]] = None,
) -> Dict[str, List[str]]:
    """Backward-compatible wrapper retained for tests/older callers.

    Semantics are now derived from unified events and runtime activity.
    """
    _ = today_status_markdown
    _ = active_work
    _ = near_term_jobs
    return build_workstream_lanes(
        timeline,
        Path("/nonexistent/jobs.json"),
        runtime={"activeRuns": []},
        now_local=now_local,
        state_path=Path("/tmp/control-room-workstream-state.compat.json"),
    )


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


def near_term_job_markers(
    jobs_file: Path,
    now_local: dt.datetime,
    horizon_minutes: int = WORKSTREAM_NEXT_JOB_HORIZON_MINUTES,
    limit: int = 3,
) -> List[str]:
    """Return near-term scheduled jobs as next-lane candidates."""
    content = read_text(jobs_file)
    if not content:
        return []

    try:
        doc = json.loads(content)
    except json.JSONDecodeError:
        return []

    now_utc = now_local.astimezone(dt.timezone.utc)
    horizon = now_utc + dt.timedelta(minutes=horizon_minutes)
    candidates: List[Tuple[int, str]] = []

    for job in doc.get("jobs", []):
        if not isinstance(job, dict) or not job.get("enabled"):
            continue

        state = job.get("state", {})
        next_run_ms = state.get("nextRunAtMs")
        if not isinstance(next_run_ms, int):
            continue

        next_run_utc = dt.datetime.fromtimestamp(next_run_ms / 1000, dt.timezone.utc)
        if next_run_utc < now_utc or next_run_utc > horizon:
            continue

        local_label = next_run_utc.astimezone(now_local.tzinfo).strftime("%H:%M")
        name = str(job.get("name", "")).strip()
        if not name:
            continue
        candidates.append((next_run_ms, f"{local_label} — Scheduled job: {name}"))

    candidates.sort(key=lambda pair: pair[0])
    return [text for _, text in candidates[:limit]]


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



def build_skill_tier_ladder(spec: Dict[str, Any]) -> List[Dict[str, Any]]:
    domain_name = str(spec.get("name") or "this domain")
    ladder: List[Dict[str, Any]] = []
    for entry in SKILL_TIER_FRAMEWORK:
        tier_value = int(entry.get("tier", 0))
        if tier_value < 1 or tier_value > SKILL_MAX_TIER:
            continue
        ladder.append(
            {
                "tier": tier_value,
                "title": str(entry.get("title") or f"Tier {tier_value}"),
                "definition": str(entry.get("definition") or "").format(domain=domain_name),
                "difference": str(entry.get("difference") or ""),
            }
        )

    ladder.sort(key=lambda item: int(item.get("tier", 0)))
    return ladder


def gather_skill_artifacts(workspace_root: Path, now_local: dt.datetime) -> List[Tuple[str, str]]:
    artifacts: List[Tuple[str, str]] = []
    memory_root = workspace_root / "memory"
    for offset in range(0, 7):
        target = now_local - dt.timedelta(days=offset)
        path = memory_root / f"{target.strftime('%Y-%m-%d')}.md"
        text = read_text(path)
        if text:
            artifacts.append((str(path), text.lower()))

    clawprime_path = workspace_root / CLAWPRIME_MEMORY_FILE
    clawprime_text = read_text(clawprime_path)
    if clawprime_text:
        artifacts.append((str(clawprime_path), clawprime_text.lower()))
    return artifacts


def build_skills_payload(workspace_root: Path, now_local: dt.datetime) -> Dict[str, Any]:
    artifacts = gather_skill_artifacts(workspace_root, now_local)
    weighted_text = "\n".join(text for _, text in artifacts)
    artifact_sources = [path for path, _ in artifacts]

    skill_nodes: List[Dict[str, Any]] = []
    active_count = 0
    planned_count = 0
    locked_count = 0

    for graph_tier, spec in enumerate(SKILL_CATALOG, start=1):
        skill_id = spec["id"]
        hits = 0
        for keyword in SKILL_KEYWORDS.get(skill_id, ()): 
            hits += weighted_text.count(keyword)

        progress = max(0.0, min(1.0, hits / 8.0))
        inferred_tier = max(0, min(SKILL_MAX_TIER, int(progress * SKILL_MAX_TIER)))
        if progress > 0 and inferred_tier == 0:
            inferred_tier = 1

        deps = spec.get("dependencies", [])
        deps_met = all(any(node.get("id") == dep and node.get("state") == "active" for node in skill_nodes) for dep in deps)

        current_tier = inferred_tier if deps_met else 0
        next_tier = current_tier + 1 if current_tier < SKILL_MAX_TIER else None
        tier_ladder = build_skill_tier_ladder(spec)
        next_unlock = (
            tier_ladder[next_tier - 1]["difference"]
            if next_tier is not None and len(tier_ladder) >= next_tier
            else None
        )

        if current_tier >= 3 and deps_met:
            state = "active"
            active_count += 1
            learned_at = now_local.date().isoformat()
        elif current_tier > 0 and deps_met:
            state = "planned"
            planned_count += 1
            learned_at = None
        else:
            state = "locked"
            locked_count += 1
            learned_at = None

        skill_nodes.append(
            {
                "id": skill_id,
                "name": spec["name"],
                "description": spec["description"],
                "effect": spec["effect"],
                "state": state,
                "tier": graph_tier,
                "currentTier": current_tier,
                "maxTier": SKILL_MAX_TIER,
                "nextTier": next_tier,
                "nextUnlock": next_unlock,
                "tierLadder": tier_ladder,
                "dependencies": deps,
                "learnedAt": learned_at,
                "level": current_tier,
                "progress": round(progress, 2),
            }
        )

    seed_input = "|".join(artifact_sources + [now_local.strftime("%Y-%m-%d")])
    deterministic_seed = hashlib.sha256(seed_input.encode("utf-8")).hexdigest()[:12]
    return {
        "activeCount": active_count,
        "plannedCount": planned_count,
        "lockedCount": locked_count,
        "nodes": skill_nodes,
        "evolution": {
            "sourceArtifacts": artifact_sources,
            "deterministicSeed": deterministic_seed,
            "lastProcessedAt": now_local.isoformat(),
            "mode": "keyword-scan-v1",
        },
    }

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


def parse_timestamp_ms(value: Any) -> Optional[int]:
    if isinstance(value, int):
        return value
    if not isinstance(value, str) or not value.strip():
        return None

    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"

    try:
        parsed = dt.datetime.fromisoformat(normalized)
    except ValueError:
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return int(parsed.timestamp() * 1000)


def normalize_runtime_model(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    if "/" not in cleaned and cleaned.startswith("gpt-"):
        return f"openai-codex/{cleaned}"
    return cleaned


def normalize_runtime_thinking(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    cleaned = value.strip().lower().replace("-", "_").replace(" ", "_")
    if not cleaned:
        return None

    aliases = {
        "min": "minimal",
        "very_high": "extra_high",
        "maximum": "extra_high",
        "max": "extra_high",
    }
    canonical = aliases.get(cleaned, cleaned)
    if canonical in {"minimal", "low", "medium", "high", "extra_high"}:
        return canonical
    return canonical


def read_jsonl_tail(path: Path, max_lines: int = 600) -> List[Dict[str, Any]]:
    """Read the tail of a jsonl file and parse valid JSON objects."""
    if not path.exists():
        return []

    parsed: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for raw in deque(handle, maxlen=max_lines):
            line = raw.strip()
            if not line:
                continue
            try:
                doc = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(doc, dict):
                parsed.append(doc)
    return parsed


def extract_user_text(content: Any) -> str:
    if isinstance(content, str):
        return content.strip()
    if not isinstance(content, list):
        return ""

    parts: List[str] = []
    for item in content:
        if not isinstance(item, dict):
            continue
        if item.get("type") != "text":
            continue
        text = item.get("text")
        if isinstance(text, str) and text.strip():
            parts.append(text.strip())
    return " ".join(parts).strip()


def summarize_main_task(text: str) -> str:
    compact = " ".join(part for part in text.split() if part)
    if not compact:
        return "Main session task"
    return compact[:140] + "…" if len(compact) > 140 else compact


def is_live_pid(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def main_session_lock_active(session_file: Path, now_ms: int) -> bool:
    lock_file = session_file.with_suffix(f"{session_file.suffix}.lock")
    if not lock_file.exists():
        return False

    try:
        lock_doc = json.loads(lock_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False

    if not isinstance(lock_doc, dict):
        return False

    created_at_ms = parse_timestamp_ms(lock_doc.get("createdAt"))
    if created_at_ms is not None and now_ms - created_at_ms > MAIN_SESSION_LOCK_STALE_MS:
        return False

    pid = lock_doc.get("pid")
    if isinstance(pid, int):
        return is_live_pid(pid)

    return created_at_ms is not None and now_ms - created_at_ms <= MAIN_SESSION_LOCK_STALE_MS


def normalize_tool_call_id(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    # Tool results may include suffix metadata like `call_x|fc_x`.
    return cleaned.split("|", 1)[0]


def collect_main_session_tool_events(
    events: List[Dict[str, Any]],
    since_ms: int,
) -> Tuple[List[Tuple[int, str]], int]:
    tool_events: List[Tuple[int, str]] = []
    pending_call_ids: set[str] = set()

    for event in events:
        event_ms = parse_timestamp_ms(event.get("timestamp"))
        if event_ms is None or event_ms < since_ms:
            continue

        message = event.get("message")
        if not isinstance(message, dict):
            continue

        role = message.get("role")
        if role == "toolResult":
            tool_name = message.get("toolName")
            if not isinstance(tool_name, str) or not tool_name.strip():
                tool_name = "tool"
            tool_events.append((event_ms, tool_name.strip()))

            result_id = normalize_tool_call_id(message.get("toolCallId"))
            if result_id is not None:
                pending_call_ids.discard(result_id)
            continue

        if role != "assistant":
            continue

        content = message.get("content")
        if not isinstance(content, list):
            continue

        for item in content:
            if not isinstance(item, dict) or item.get("type") != "toolCall":
                continue
            tool_name = item.get("name") or item.get("toolName")
            if not isinstance(tool_name, str) or not tool_name.strip():
                tool_name = "tool"
            tool_events.append((event_ms, tool_name.strip()))

            call_id = normalize_tool_call_id(item.get("id") or item.get("toolCallId"))
            if call_id is not None:
                pending_call_ids.add(call_id)

    return tool_events, len(pending_call_ids)


def active_main_session_run(
    main_session_meta: Dict[str, Any],
    now_ms: int,
    max_age_ms: int = MAIN_SESSION_RUNTIME_MAX_AGE_MS,
) -> Optional[Dict[str, Any]]:
    """Detect active main-session execution work from recent tool activity.

    Plain user/assistant chat with no tool activity is intentionally excluded.
    """
    session_file_raw = main_session_meta.get("sessionFile")
    if isinstance(session_file_raw, str) and session_file_raw.strip():
        session_file = Path(session_file_raw)
    else:
        session_id = main_session_meta.get("sessionId")
        if not isinstance(session_id, str) or not session_id.strip():
            return None
        session_file = SESSIONS_STORE_PATH.parent / f"{session_id}.jsonl"

    events = read_jsonl_tail(session_file)
    if not events:
        return None

    latest_user_ms: Optional[int] = None
    latest_user_text = ""
    for event in reversed(events):
        message = event.get("message")
        if not isinstance(message, dict) or message.get("role") != "user":
            continue

        latest_user_ms = parse_timestamp_ms(message.get("timestamp"))
        if latest_user_ms is None:
            latest_user_ms = parse_timestamp_ms(event.get("timestamp"))

        latest_user_text = extract_user_text(message.get("content"))
        break

    if latest_user_ms is None:
        return None

    tool_events, pending_call_count = collect_main_session_tool_events(events, latest_user_ms)
    if not tool_events:
        return None

    last_tool_ms = max(item[0] for item in tool_events)
    if pending_call_count > 0:
        # Keep in-flight tool execution visible for longer windows.
        if now_ms - last_tool_ms > MAIN_SESSION_PENDING_CALL_MAX_AGE_MS:
            return None
        # If the lock is missing but the activity is very recent, still consider it running.
        lock_active = main_session_lock_active(session_file, now_ms)
        if not lock_active and now_ms - last_tool_ms > max_age_ms:
            return None
    elif now_ms - last_tool_ms > max_age_ms:
        return None

    started_at_ms = min(item[0] for item in tool_events)
    started_local = (
        dt.datetime.fromtimestamp(started_at_ms / 1000, dt.timezone.utc)
        .astimezone()
        .strftime("%Y-%m-%d %H:%M:%S")
    )

    unique_tools = sorted({item[1] for item in tool_events})
    tool_summary = ", ".join(unique_tools[:3])
    if len(unique_tools) > 3:
        tool_summary = f"{tool_summary}, +{len(unique_tools) - 3} more"

    task_summary = summarize_main_task(latest_user_text)
    return {
        "jobId": "interactive:main-session",
        "jobName": task_summary,
        "sessionId": MAIN_SESSION_KEY,
        "sessionKey": MAIN_SESSION_KEY,
        "summary": f"{task_summary} (tools: {tool_summary})" if tool_summary else task_summary,
        "startedAtMs": started_at_ms,
        "startedAtLocal": started_local,
        "runningForMs": max(0, now_ms - started_at_ms),
        "activityType": "interactive",
    }


def summarize_subagent_task(entry: Dict[str, Any]) -> Optional[str]:
    task = entry.get("task")
    if not isinstance(task, str):
        return None

    cleaned = " ".join(line.strip() for line in task.splitlines() if line.strip())
    if not cleaned:
        return None

    return cleaned[:180] + "…" if len(cleaned) > 180 else cleaned


def resolve_subagent_label(entry: Dict[str, Any], run_id: str) -> str:
    """Return the most descriptive label available for sub-agent runs."""
    label = entry.get("label")
    if isinstance(label, str) and label.strip() and label.strip().lower() != "background task":
        return label.strip()

    task_summary = summarize_subagent_task(entry)
    if task_summary:
        return task_summary

    invoke_command = entry.get("invokeCommand")
    if isinstance(invoke_command, str) and invoke_command.strip():
        return invoke_command.strip()

    command = entry.get("command")
    if isinstance(command, list):
        parts = [str(part).strip() for part in command if str(part).strip()]
        if parts:
            return " ".join(parts[:6])

    child_session_key = entry.get("childSessionKey")
    if isinstance(child_session_key, str) and child_session_key.strip():
        return f"Subagent task ({child_session_key.split(':')[-1][:10]})"

    return f"Subagent task ({run_id[:10]})"


def active_subagent_runs(subagent_registry_path: Path, now_ms: int) -> List[Dict[str, Any]]:
    """Read active sub-agent/background runs from subagent registry."""
    signals = collect_subagent_runtime_signals(subagent_registry_path)
    rows = signals["candidates"]

    active: List[Dict[str, Any]] = []
    for row in rows:
        started_at_ms = row.get("startedAtMs")
        if not isinstance(started_at_ms, int):
            continue

        started_local = (
            dt.datetime.fromtimestamp(started_at_ms / 1000, dt.timezone.utc)
            .astimezone()
            .strftime("%Y-%m-%d %H:%M:%S")
        )
        active.append(
            {
                "jobId": row.get("jobId"),
                "jobName": row.get("jobName"),
                "sessionId": row.get("sessionId"),
                "sessionKey": row.get("sessionKey"),
                "summary": row.get("summary") or row.get("jobName"),
                "startedAtMs": started_at_ms,
                "startedAtLocal": started_local,
                "runningForMs": max(0, now_ms - started_at_ms),
                "activityType": "subagent",
                "model": row.get("model"),
                "thinking": row.get("thinking"),
            }
        )

    return active


def collect_cron_terminal_events(job_id: str, runs_dir: Path, cache: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    if job_id in cache:
        return cache[job_id]

    run_file = runs_dir / f"{job_id}.jsonl"
    if not run_file.exists():
        cache[job_id] = []
        return []

    events: List[Dict[str, Any]] = []
    for raw in run_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue

        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue

        if not isinstance(row, dict) or row.get("action") != "finished":
            continue

        session_id = row.get("sessionId")
        if not isinstance(session_id, str) or not session_id:
            continue

        run_key = normalize_run_key("cron", job_id=job_id, session_id=session_id)
        if run_key is None:
            continue

        event_at_ms = (
            parse_timestamp_ms(row.get("finishedAtMs"))
            or parse_timestamp_ms(row.get("finishedAt"))
            or parse_timestamp_ms(row.get("endedAt"))
            or parse_timestamp_ms(row.get("timestamp"))
            or parse_timestamp_ms(row.get("ts"))
        )
        if event_at_ms is None:
            continue

        terminal_type = str(row.get("status") or row.get("result") or "finished").lower()
        if terminal_type in {"ok", "success", "completed", "done"}:
            terminal_type = "finished"
        elif terminal_type in {"cancelled", "canceled"}:
            terminal_type = "cancelled"
        elif terminal_type in {"timeout", "timedout", "timed_out"}:
            terminal_type = "timed_out"
        elif terminal_type in {"failed", "error", "errored"}:
            terminal_type = "failed"
        elif terminal_type not in {"finished", "failed", "cancelled", "timed_out"}:
            terminal_type = "finished"

        events.append(
            {
                "runKey": run_key,
                "eventType": terminal_type,
                "eventAtMs": event_at_ms,
            }
        )

    cache[job_id] = events
    return events


def collect_subagent_runtime_signals(subagent_registry_path: Path) -> Dict[str, List[Dict[str, Any]]]:
    if not subagent_registry_path.exists():
        return {"candidates": [], "terminals": []}

    try:
        registry = json.loads(subagent_registry_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"candidates": [], "terminals": []}

    if not isinstance(registry, dict):
        return {"candidates": [], "terminals": []}

    runs = registry.get("runs")
    if not isinstance(runs, dict):
        return {"candidates": [], "terminals": []}

    candidates: List[Dict[str, Any]] = []
    terminals: List[Dict[str, Any]] = []

    for run_id, entry in runs.items():
        if not isinstance(run_id, str) or not isinstance(entry, dict):
            continue

        run_key = normalize_run_key("subagent", run_id=run_id)
        if run_key is None:
            continue

        started_at_ms = parse_timestamp_ms(entry.get("startedAt"))
        if started_at_ms is None:
            started_at_ms = parse_timestamp_ms(entry.get("createdAt"))
        if started_at_ms is None:
            continue

        ended_at_ms = parse_timestamp_ms(entry.get("endedAt"))

        label = resolve_subagent_label(entry, run_id)
        task_summary = summarize_subagent_task(entry)
        model = normalize_runtime_model(entry.get("model") or entry.get("agentModel"))
        thinking = normalize_runtime_thinking(entry.get("thinking"))

        child_session_key = entry.get("childSessionKey")
        session_key = child_session_key if isinstance(child_session_key, str) and child_session_key else f"subagent:{run_id}"
        session_id = session_key

        if ended_at_ms is not None:
            terminal_type = str(entry.get("status") or entry.get("endStatus") or "finished").lower()
            if terminal_type in {"ok", "success", "completed", "done"}:
                terminal_type = "finished"
            elif terminal_type in {"cancelled", "canceled"}:
                terminal_type = "cancelled"
            elif terminal_type in {"timeout", "timedout", "timed_out"}:
                terminal_type = "timed_out"
            elif terminal_type in {"failed", "error", "errored"}:
                terminal_type = "failed"
            elif terminal_type not in {"finished", "failed", "cancelled", "timed_out"}:
                terminal_type = "finished"

            terminals.append(
                {
                    "runKey": run_key,
                    "eventType": terminal_type,
                    "eventAtMs": ended_at_ms,
                }
            )
            continue

        last_seen_at_ms = parse_timestamp_ms(entry.get("updatedAt")) or started_at_ms
        candidates.append(
            {
                "runKey": run_key,
                "jobId": f"subagent:{run_id}",
                "jobName": label,
                "sessionId": session_id,
                "sessionKey": session_key,
                "summary": task_summary or label,
                "startedAtMs": started_at_ms,
                "lastSeenAtMs": last_seen_at_ms,
                "activityType": "subagent",
                "model": model,
                "thinking": thinking,
            }
        )

    return {"candidates": candidates, "terminals": terminals}


def load_materialized_runtime_state(
    runtime_state_path: Path,
    now_ms: int,
    max_age_ms: int,
) -> Tuple[Optional[Dict[str, Any]], str]:
    if not runtime_state_path.exists():
        return None, "materialized-state-missing"

    try:
        doc = json.loads(runtime_state_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None, "materialized-state-invalid"

    if not isinstance(doc, dict):
        return None, "materialized-state-unexpected-shape"

    materialized_at_ms = doc.get("materializedAtMs")
    if not isinstance(materialized_at_ms, int):
        materialized_at_ms = doc.get("checkedAtMs")
    if not isinstance(materialized_at_ms, int):
        return None, "materialized-state-missing-timestamp"

    if now_ms - materialized_at_ms > max_age_ms:
        return None, "materialized-state-stale"

    active_rows_raw = doc.get("activeRuns")
    if not isinstance(active_rows_raw, list):
        return None, "materialized-state-missing-active-runs"

    active_rows: List[Dict[str, Any]] = []
    for row in active_rows_raw:
        if not isinstance(row, dict):
            continue
        started_at_ms = row.get("startedAtMs")
        if not isinstance(started_at_ms, int):
            continue

        normalized = dict(row)
        normalized["runningForMs"] = max(0, now_ms - started_at_ms)
        normalized["startedAtLocal"] = (
            dt.datetime.fromtimestamp(started_at_ms / 1000, dt.timezone.utc)
            .astimezone()
            .strftime("%Y-%m-%d %H:%M:%S")
        )
        normalized["summary"] = str(row.get("summary") or row.get("jobName") or "Running activity")

        model = normalize_runtime_model(row.get("model"))
        if model is not None:
            normalized["model"] = model

        thinking = normalize_runtime_thinking(row.get("thinking"))
        if thinking is not None:
            normalized["thinking"] = thinking

        active_rows.append(normalized)

    active_rows.sort(key=lambda item: (item.get("startedAtMs", 0), item.get("runKey", "")))
    runtime = {
        "status": "running" if active_rows else "idle",
        "isIdle": len(active_rows) == 0,
        "activeCount": len(active_rows),
        "activeRuns": active_rows,
        "checkedAtMs": now_ms,
        "source": "materialized-ledger",
        "revision": str(doc.get("revision") or "rtv1-00000000"),
        "snapshotMode": str(doc.get("snapshotMode") or "live"),
        "degradedReason": str(doc.get("degradedReason") or ""),
    }
    return runtime, ""


def runtime_activity(
    jobs_file: Path,
    sessions_store_path: Path = SESSIONS_STORE_PATH,
    runs_dir: Path = CRON_RUNS_DIR,
    subagent_registry_path: Optional[Path] = None,
    max_age_ms: int = 6 * 60 * 60 * 1000,
    runtime_state_path: Path = RUNTIME_STATE_FILE,
    stale_ms: int = RUNTIME_STALE_MS,
    materialized_max_age_ms: int = RUNTIME_MATERIALIZED_MAX_AGE_MS,
) -> Dict[str, Any]:
    """Return runtime truth using materialized ledger first, reconciler fallback second."""
    now_ms = int(dt.datetime.now(dt.timezone.utc).timestamp() * 1000)

    materialized_runtime, materialized_reason = load_materialized_runtime_state(
        runtime_state_path,
        now_ms,
        materialized_max_age_ms,
    )
    if materialized_runtime is not None:
        return materialized_runtime

    jobs_doc_text = read_text(jobs_file)
    jobs_by_id: Dict[str, Dict[str, Optional[str]]] = {}
    if jobs_doc_text:
        try:
            jobs_doc = json.loads(jobs_doc_text)
            for job in jobs_doc.get("jobs", []):
                if not isinstance(job, dict) or not job.get("id"):
                    continue
                job_id = str(job.get("id"))
                payload = job.get("payload") if isinstance(job.get("payload"), dict) else {}
                jobs_by_id[job_id] = {
                    "name": str(job.get("name", "")),
                    "model": normalize_runtime_model(payload.get("model")),
                    "thinking": normalize_runtime_thinking(payload.get("thinking")),
                }
        except json.JSONDecodeError:
            jobs_by_id = {}

    candidates: List[Dict[str, Any]] = []
    terminal_events: List[Dict[str, Any]] = []

    sessions_reason = ""
    if sessions_store_path.exists():
        try:
            sessions_doc = json.loads(sessions_store_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            sessions_doc = None
            sessions_reason = "sessions-store-invalid"

        if isinstance(sessions_doc, dict):
            terminal_cache: Dict[str, List[Dict[str, Any]]] = {}
            for key, meta in sessions_doc.items():
                if not isinstance(key, str) or not isinstance(meta, dict):
                    continue

                match = CRON_RUN_SESSION_KEY_RE.match(key)
                if not match:
                    continue

                job_id, session_id = match.groups()
                started_at_ms = parse_timestamp_ms(meta.get("updatedAt"))
                if started_at_ms is None:
                    continue

                run_key = normalize_run_key("cron", job_id=job_id, session_id=session_id)
                if run_key is None:
                    continue

                job_meta = jobs_by_id.get(job_id) or {}
                job_name = str(job_meta.get("name") or f"Unknown job ({job_id[:8]})")
                normalized_job_name = job_name.lower()
                if any(token in normalized_job_name for token in EXCLUDED_RUNTIME_JOB_NAME_SUBSTRINGS):
                    continue

                session_model = normalize_runtime_model(meta.get("model"))
                session_thinking = normalize_runtime_thinking(meta.get("thinking"))
                model = session_model or job_meta.get("model")
                thinking = session_thinking or job_meta.get("thinking")

                candidates.append(
                    {
                        "runKey": run_key,
                        "jobId": job_id,
                        "jobName": job_name,
                        "sessionId": session_id,
                        "sessionKey": key,
                        "summary": job_name,
                        "startedAtMs": started_at_ms,
                        "lastSeenAtMs": started_at_ms,
                        "activityType": "cron",
                        "model": model,
                        "thinking": thinking,
                    }
                )
                terminal_events.extend(collect_cron_terminal_events(job_id, runs_dir, terminal_cache))
        elif not sessions_reason:
            sessions_reason = "sessions-store-unexpected-shape"
    else:
        sessions_reason = "sessions-store-missing"

    if subagent_registry_path is not None:
        subagent_signals = collect_subagent_runtime_signals(subagent_registry_path)
        candidates.extend(subagent_signals["candidates"])
        terminal_events.extend(subagent_signals["terminals"])

    reconciled = reconcile(
        now_ms=now_ms,
        candidates=candidates,
        terminal_events=terminal_events,
        stale_ms=min(max_age_ms, stale_ms),
    )

    active_runs: List[Dict[str, Any]] = []
    for row in reconciled["activeRuns"]:
        active_runs.append(
            {
                "jobId": row.get("jobId"),
                "jobName": row.get("jobName"),
                "sessionId": row.get("sessionId"),
                "sessionKey": row.get("sessionKey"),
                "summary": row.get("summary"),
                "startedAtMs": row.get("startedAtMs"),
                "startedAtLocal": row.get("startedAtLocal"),
                "runningForMs": row.get("runningForMs"),
                "activityType": row.get("activityType", "cron"),
                "model": row.get("model"),
                "thinking": row.get("thinking"),
            }
        )

    degraded_bits = [bit for bit in [materialized_reason, sessions_reason] if bit]
    return {
        "status": "running" if active_runs else "idle",
        "isIdle": len(active_runs) == 0,
        "activeCount": len(active_runs),
        "activeRuns": active_runs,
        "checkedAtMs": now_ms,
        "source": "live-reconciler",
        "revision": f"rtv1-{now_ms:08d}",
        "snapshotMode": "live",
        "degradedReason": ", ".join(degraded_bits),
        "droppedTerminalCount": reconciled.get("droppedTerminalCount", 0),
        "droppedStaleCount": reconciled.get("droppedStaleCount", 0),
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

    next_jobs_rows = next_jobs(jobs_file)
    runtime = runtime_activity(jobs_file, subagent_registry_path=SUBAGENT_REGISTRY_PATH)
    workstream = build_workstream_lanes(
        timeline,
        jobs_file,
        runtime,
        now_local,
        WORKSTREAM_STATE_FILE,
    )

    return {
        "generatedAt": dt.datetime.now(dt.timezone.utc).isoformat(),
        "generatedAtLocal": now_local.strftime("%Y-%m-%d %H:%M %Z"),
        "controlRoomVersion": control_room_version(),
        "currentFocus": current_focus,
        "activeWork": active_work,
        "reliability": reliability_status(workspace_root),
        "timeline": timeline,
        "nextJobs": next_jobs_rows,
        "findings": recent_findings(memory_text),
        "workstream": workstream,
        "charts": {
            "jobSuccessTrend": job_success_trend(jobs_file),
            "reliabilityTrend": reliability_trend(Path("/Users/seankudrna/.openclaw/logs/reliability-watchdog.jsonl")),
        },
        "activity": recent_activity(memory_text),
        "skills": build_skills_payload(workspace_root, now_local),
        "runtime": runtime,
    }


def sanitize_payload_for_static_snapshot(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Return a snapshot-safe payload for committed fallback JSON files.

    Static fallback snapshots should never contain live `RUNNING` rows because they can
    be cached and appear stale. Live runtime visibility is delivered via gist publish.
    """
    out = dict(payload)
    runtime = payload.get("runtime")
    if not isinstance(runtime, dict):
        return out

    sanitized_runtime = dict(runtime)
    sanitized_runtime["status"] = "idle"
    sanitized_runtime["isIdle"] = True
    sanitized_runtime["activeCount"] = 0
    sanitized_runtime["activeRuns"] = []
    sanitized_runtime["source"] = "fallback-static"
    sanitized_runtime["snapshotMode"] = "fallback-sanitized"
    sanitized_runtime["degradedReason"] = "Static snapshot cannot carry live runtime rows"
    sanitized_runtime["revision"] = str(sanitized_runtime.get("revision") or "rtv1-00000000")

    out["runtime"] = sanitized_runtime
    return out
