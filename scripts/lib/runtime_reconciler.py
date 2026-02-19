#!/usr/bin/env python3
"""Runtime reconciler for deterministic active-run truth."""

from __future__ import annotations

import datetime as dt
from typing import Any, Dict, Iterable, List, Optional, Tuple

from scripts.lib.runtime_events import is_terminal_event_type


def normalize_run_key(
    activity_type: str,
    *,
    job_id: Optional[str] = None,
    session_id: Optional[str] = None,
    run_id: Optional[str] = None,
) -> Optional[str]:
    normalized_type = (activity_type or "").strip().lower()
    if normalized_type == "cron":
        if not job_id or not session_id:
            return None
        return f"cron:{job_id}:{session_id}"

    if normalized_type == "subagent":
        if not run_id:
            return None
        return f"subagent:{run_id}"

    return None


def _normalize_candidate(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    run_key = row.get("runKey")
    started_at_ms = row.get("startedAtMs")
    if not isinstance(run_key, str) or not run_key:
        return None
    if not isinstance(started_at_ms, int):
        return None

    last_seen_at_ms = row.get("lastSeenAtMs")
    if not isinstance(last_seen_at_ms, int):
        last_seen_at_ms = started_at_ms

    out = dict(row)
    out["runKey"] = run_key
    out["startedAtMs"] = started_at_ms
    out["lastSeenAtMs"] = max(last_seen_at_ms, started_at_ms)
    return out


def collect_candidates(rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Collect canonical candidate rows, de-duplicated by runKey."""
    by_run_key: Dict[str, Dict[str, Any]] = {}

    for raw in rows:
        if not isinstance(raw, dict):
            continue
        candidate = _normalize_candidate(raw)
        if candidate is None:
            continue

        run_key = candidate["runKey"]
        current = by_run_key.get(run_key)
        if current is None:
            by_run_key[run_key] = candidate
            continue

        merged = dict(current)
        merged["startedAtMs"] = min(current["startedAtMs"], candidate["startedAtMs"])
        merged["lastSeenAtMs"] = max(current["lastSeenAtMs"], candidate["lastSeenAtMs"])

        for field in ("jobName", "summary", "sessionId", "sessionKey", "jobId", "activityType", "model", "thinking"):
            if not merged.get(field) and candidate.get(field):
                merged[field] = candidate[field]

        by_run_key[run_key] = merged

    return sorted(by_run_key.values(), key=lambda row: (row["startedAtMs"], row["runKey"]))


def collect_terminals(events: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Collect latest terminal event per run key."""
    terminals: Dict[str, Dict[str, Any]] = {}

    for raw in events:
        if not isinstance(raw, dict):
            continue

        run_key = raw.get("runKey")
        event_type = raw.get("eventType")
        event_at_ms = raw.get("eventAtMs")

        if not isinstance(run_key, str) or not run_key:
            continue
        if not is_terminal_event_type(event_type):
            continue
        if not isinstance(event_at_ms, int):
            continue

        current = terminals.get(run_key)
        if current is None or event_at_ms >= current.get("eventAtMs", 0):
            terminals[run_key] = {
                "runKey": run_key,
                "eventType": event_type,
                "eventAtMs": event_at_ms,
            }

    return terminals


def reconcile(
    *,
    now_ms: int,
    candidates: Iterable[Dict[str, Any]],
    terminal_events: Iterable[Dict[str, Any]],
    stale_ms: int,
) -> Dict[str, Any]:
    """Reconcile active runtime rows using terminal dominance + stale expiry."""
    normalized = collect_candidates(candidates)
    terminals = collect_terminals(terminal_events)

    active_rows: List[Dict[str, Any]] = []
    dropped_terminal = 0
    dropped_stale = 0

    for row in normalized:
        run_key = row["runKey"]
        terminal = terminals.get(run_key)
        if terminal is not None:
            terminal_at_ms = terminal.get("eventAtMs", 0)
            if terminal_at_ms >= row["startedAtMs"]:
                dropped_terminal += 1
                continue

        if now_ms - row["lastSeenAtMs"] > stale_ms:
            dropped_stale += 1
            continue

        active = dict(row)
        active["runningForMs"] = max(0, now_ms - row["startedAtMs"])
        active["startedAtLocal"] = (
            dt.datetime.fromtimestamp(row["startedAtMs"] / 1000, dt.timezone.utc)
            .astimezone()
            .strftime("%Y-%m-%d %H:%M:%S")
        )
        active_rows.append(active)

    active_rows.sort(key=lambda item: (item.get("startedAtMs", 0), item.get("runKey", "")))

    return {
        "activeRuns": active_rows,
        "activeCount": len(active_rows),
        "droppedTerminalCount": dropped_terminal,
        "droppedStaleCount": dropped_stale,
        "terminalCount": len(terminals),
    }
