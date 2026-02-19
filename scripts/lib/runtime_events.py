#!/usr/bin/env python3
"""Runtime event helpers for deterministic runtime truth materialization."""

from __future__ import annotations

import hashlib
from typing import Any, Dict, Iterable, List, Tuple

SOURCE_PRIORITY = {
    "cron-runs": 0,
    "subagent-registry": 1,
    "sessions-store": 2,
}

TERMINAL_EVENT_TYPES = {
    "finished",
    "failed",
    "cancelled",
    "timed_out",
    "stale_expired",
}

RUNNING_EVENT_TYPES = {
    "started",
    "heartbeat",
}


def normalize_terminal_event_type(value: Any) -> str:
    """Normalize heterogeneous terminal labels to canonical runtime values."""
    if not isinstance(value, str):
        return "finished"

    normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
    if normalized in TERMINAL_EVENT_TYPES:
        return normalized
    if normalized in {"ok", "success", "succeeded", "complete", "completed", "done"}:
        return "finished"
    if normalized in {"timeout", "timedout", "timed_out"}:
        return "timed_out"
    if normalized in {"error", "errored", "failure"}:
        return "failed"
    if normalized in {"canceled"}:
        return "cancelled"
    return "finished"


def deterministic_event_id(
    run_key: str,
    event_type: str,
    event_at_ms: int,
    source: str,
    source_offset: str,
) -> str:
    material = f"{run_key}|{event_type}|{event_at_ms}|{source}|{source_offset}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def build_event(
    *,
    run_key: str,
    event_type: str,
    event_at_ms: int,
    source: str,
    source_offset: str,
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    """Build canonical runtime event with deterministic id."""
    normalized_type = normalize_terminal_event_type(event_type) if event_type not in RUNNING_EVENT_TYPES else event_type
    return {
        "eventId": deterministic_event_id(run_key, normalized_type, event_at_ms, source, source_offset),
        "runKey": run_key,
        "eventType": normalized_type,
        "eventAtMs": event_at_ms,
        "source": source,
        "sourceOffset": source_offset,
        "payload": payload,
    }


def source_priority(source: Any) -> int:
    if not isinstance(source, str):
        return 99
    return SOURCE_PRIORITY.get(source, 50)


def event_sort_key(event: Dict[str, Any]) -> Tuple[int, int, str, str]:
    event_at_ms = event.get("eventAtMs")
    if not isinstance(event_at_ms, int):
        event_at_ms = 0
    source = event.get("source")
    source_offset = event.get("sourceOffset")
    event_id = event.get("eventId")
    return (
        event_at_ms,
        source_priority(source),
        str(source_offset or ""),
        str(event_id or ""),
    )


def sort_events(events: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(list(events), key=event_sort_key)


def is_terminal_event_type(event_type: Any) -> bool:
    return isinstance(event_type, str) and event_type in TERMINAL_EVENT_TYPES
