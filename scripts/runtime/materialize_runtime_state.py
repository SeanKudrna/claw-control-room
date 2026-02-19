#!/usr/bin/env python3
"""Materialize active runtime truth from append-only runtime event journal."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.lib.runtime_events import RUNNING_EVENT_TYPES, is_terminal_event_type, sort_events

REVISION_RE = re.compile(r"^rtv1-(\d+)$")


def read_events(events_file: Path) -> List[Dict[str, Any]]:
    if not events_file.exists():
        return []

    events: List[Dict[str, Any]] = []
    for raw in events_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            events.append(row)
    return sort_events(events)


def parse_revision_number(runtime_state_file: Path) -> int:
    if not runtime_state_file.exists():
        return 0

    try:
        current = json.loads(runtime_state_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return 0

    if not isinstance(current, dict):
        return 0

    revision = current.get("revision")
    if not isinstance(revision, str):
        return 0

    match = REVISION_RE.match(revision)
    if not match:
        return 0

    try:
        return int(match.group(1))
    except ValueError:
        return 0


def make_runtime_row(run_key: str, state: Dict[str, Any], now_ms: int) -> Dict[str, Any]:
    started_at_ms = int(state.get("startedAtMs") or state.get("firstSeenAtMs") or now_ms)
    last_seen_at_ms = int(state.get("lastSeenAtMs") or started_at_ms)

    started_local = (
        dt.datetime.fromtimestamp(started_at_ms / 1000, dt.timezone.utc)
        .astimezone()
        .strftime("%Y-%m-%d %H:%M:%S")
    )

    row = {
        "runKey": run_key,
        "jobId": str(state.get("jobId") or run_key),
        "jobName": str(state.get("jobName") or state.get("summary") or "Running activity"),
        "sessionId": str(state.get("sessionId") or state.get("sessionKey") or run_key),
        "sessionKey": str(state.get("sessionKey") or state.get("sessionId") or run_key),
        "summary": str(state.get("summary") or state.get("jobName") or "Running activity"),
        "startedAtMs": started_at_ms,
        "lastSeenAtMs": last_seen_at_ms,
        "startedAtLocal": started_local,
        "runningForMs": max(0, now_ms - started_at_ms),
        "activityType": str(state.get("activityType") or "cron"),
    }

    model = state.get("model")
    if isinstance(model, str) and model.strip():
        row["model"] = model.strip()

    thinking = state.get("thinking")
    if isinstance(thinking, str) and thinking.strip():
        row["thinking"] = thinking.strip()

    return row


def reduce_events(
    events: Iterable[Dict[str, Any]],
    *,
    now_ms: int,
    stale_ms: int,
) -> Tuple[List[Dict[str, Any]], Dict[str, Dict[str, Any]], int]:
    active: Dict[str, Dict[str, Any]] = {}
    terminals: Dict[str, Dict[str, Any]] = {}

    for event in sort_events(events):
        run_key = event.get("runKey")
        event_type = event.get("eventType")
        event_at_ms = event.get("eventAtMs")

        if not isinstance(run_key, str) or not run_key:
            continue
        if not isinstance(event_type, str) or not isinstance(event_at_ms, int):
            continue

        if run_key in terminals:
            # Absorbing terminal states: never reopen.
            continue

        payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}

        if is_terminal_event_type(event_type):
            terminals[run_key] = {
                "eventType": event_type,
                "eventAtMs": event_at_ms,
            }
            active.pop(run_key, None)
            continue

        if event_type not in RUNNING_EVENT_TYPES:
            continue

        row = active.get(run_key, {})
        started_at_ms = row.get("startedAtMs")
        candidate_start = payload.get("startedAtMs") if isinstance(payload.get("startedAtMs"), int) else event_at_ms
        if isinstance(started_at_ms, int):
            started_at_ms = min(started_at_ms, candidate_start)
        else:
            started_at_ms = candidate_start

        last_seen_at_ms = row.get("lastSeenAtMs")
        candidate_seen = payload.get("lastSeenAtMs") if isinstance(payload.get("lastSeenAtMs"), int) else event_at_ms
        if isinstance(last_seen_at_ms, int):
            last_seen_at_ms = max(last_seen_at_ms, candidate_seen)
        else:
            last_seen_at_ms = candidate_seen

        merged = {
            "startedAtMs": started_at_ms,
            "lastSeenAtMs": last_seen_at_ms,
            "firstSeenAtMs": row.get("firstSeenAtMs", event_at_ms),
            "jobId": payload.get("jobId") or row.get("jobId"),
            "jobName": payload.get("jobName") or row.get("jobName"),
            "sessionId": payload.get("sessionId") or row.get("sessionId"),
            "sessionKey": payload.get("sessionKey") or row.get("sessionKey"),
            "summary": payload.get("summary") or row.get("summary") or payload.get("jobName"),
            "activityType": payload.get("activityType") or row.get("activityType") or "cron",
            "model": payload.get("model") or row.get("model"),
            "thinking": payload.get("thinking") or row.get("thinking"),
        }
        active[run_key] = merged

    dropped_stale = 0
    for run_key in list(active.keys()):
        last_seen_at_ms = active[run_key].get("lastSeenAtMs")
        if not isinstance(last_seen_at_ms, int):
            active.pop(run_key, None)
            dropped_stale += 1
            continue

        if now_ms - last_seen_at_ms > stale_ms:
            terminals[run_key] = {
                "eventType": "stale_expired",
                "eventAtMs": now_ms,
            }
            active.pop(run_key, None)
            dropped_stale += 1

    active_rows = [make_runtime_row(run_key, state, now_ms) for run_key, state in active.items()]
    active_rows.sort(key=lambda row: (row.get("startedAtMs", 0), row.get("runKey", "")))
    return active_rows, terminals, dropped_stale


def materialize_runtime_state(
    *,
    events_file: Path,
    runtime_state_file: Path,
    now_ms: int | None = None,
    stale_ms: int = 10 * 60 * 1000,
) -> Dict[str, Any]:
    if now_ms is None:
        now_ms = int(dt.datetime.now(dt.timezone.utc).timestamp() * 1000)

    events = read_events(events_file)
    active_rows, terminals, dropped_stale = reduce_events(events, now_ms=now_ms, stale_ms=stale_ms)

    revision_num = parse_revision_number(runtime_state_file) + 1
    runtime_state = {
        "status": "running" if active_rows else "idle",
        "isIdle": len(active_rows) == 0,
        "activeCount": len(active_rows),
        "activeRuns": active_rows,
        "checkedAtMs": now_ms,
        "source": "materialized-ledger",
        "revision": f"rtv1-{revision_num:08d}",
        "snapshotMode": "live",
        "degradedReason": "",
        "materializedAtMs": now_ms,
        "terminalCount": len(terminals),
        "droppedStaleCount": dropped_stale,
    }

    runtime_state_file.parent.mkdir(parents=True, exist_ok=True)
    runtime_state_file.write_text(json.dumps(runtime_state, indent=2) + "\n", encoding="utf-8")
    return runtime_state


def main() -> int:
    parser = argparse.ArgumentParser(description="Materialize runtime state from runtime-events journal")
    parser.add_argument("--events-file", default="/Users/seankudrna/.openclaw/workspace/status/runtime-events.jsonl")
    parser.add_argument("--out", default="/Users/seankudrna/.openclaw/workspace/status/runtime-state.json")
    parser.add_argument("--stale-ms", type=int, default=10 * 60 * 1000)
    args = parser.parse_args()

    runtime_state = materialize_runtime_state(
        events_file=Path(args.events_file),
        runtime_state_file=Path(args.out),
        stale_ms=args.stale_ms,
    )
    print(
        "runtime materialized: "
        f"revision={runtime_state['revision']} active={runtime_state['activeCount']} terminals={runtime_state['terminalCount']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
