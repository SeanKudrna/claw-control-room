#!/usr/bin/env python3
"""Collect runtime lifecycle events into append-only JSONL journal."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.lib.runtime_events import build_event, normalize_terminal_event_type, sort_events
from scripts.lib.runtime_reconciler import normalize_run_key

CRON_RUN_SESSION_KEY_RE = re.compile(r"^agent:main:cron:([^:]+):run:([^:]+)$")


def read_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def parse_timestamp_ms(value: Any) -> int | None:
    if isinstance(value, int):
        if value > 10_000_000_000:
            return value
        if value > 0:
            return value * 1000
        return None

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


def normalize_runtime_model(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    if "/" not in cleaned and cleaned.startswith("gpt-"):
        return f"openai-codex/{cleaned}"
    return cleaned


def normalize_runtime_thinking(value: Any) -> str | None:
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
    return canonical


def load_jobs(jobs_file: Path) -> Dict[str, Dict[str, str | None]]:
    doc = read_json(jobs_file)
    if not isinstance(doc, dict):
        return {}

    jobs: Dict[str, Dict[str, str | None]] = {}
    for row in doc.get("jobs", []):
        if not isinstance(row, dict):
            continue
        job_id = row.get("id")
        if not isinstance(job_id, str) or not job_id:
            continue

        payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
        jobs[job_id] = {
            "name": str(row.get("name") or f"Unknown job ({job_id[:8]})"),
            "model": normalize_runtime_model(payload.get("model")),
            "thinking": normalize_runtime_thinking(payload.get("thinking")),
        }
    return jobs


def collect_session_events(sessions_file: Path, jobs_by_id: Dict[str, Dict[str, str | None]]) -> List[Dict[str, Any]]:
    doc = read_json(sessions_file)
    if not isinstance(doc, dict):
        return []

    events: List[Dict[str, Any]] = []
    for session_key, meta in doc.items():
        if not isinstance(session_key, str) or not isinstance(meta, dict):
            continue

        match = CRON_RUN_SESSION_KEY_RE.match(session_key)
        if not match:
            continue

        job_id, session_id = match.groups()
        run_key = normalize_run_key("cron", job_id=job_id, session_id=session_id)
        if run_key is None:
            continue

        event_at_ms = parse_timestamp_ms(meta.get("updatedAt"))
        if event_at_ms is None:
            continue

        job_meta = jobs_by_id.get(job_id) or {}
        job_name = str(job_meta.get("name") or f"Unknown job ({job_id[:8]})")
        session_model = normalize_runtime_model(meta.get("model"))
        session_thinking = normalize_runtime_thinking(meta.get("thinking"))
        payload = {
            "jobId": job_id,
            "jobName": job_name,
            "sessionId": session_id,
            "sessionKey": session_key,
            "summary": job_name,
            "startedAtMs": event_at_ms,
            "lastSeenAtMs": event_at_ms,
            "activityType": "cron",
            "model": session_model or job_meta.get("model"),
            "thinking": session_thinking or job_meta.get("thinking"),
        }
        events.append(
            build_event(
                run_key=run_key,
                event_type="heartbeat",
                event_at_ms=event_at_ms,
                source="sessions-store",
                source_offset=f"sessions:{session_key}",
                payload=payload,
            )
        )

    return events


def collect_cron_terminal_events(runs_dir: Path) -> List[Dict[str, Any]]:
    if not runs_dir.exists():
        return []

    events: List[Dict[str, Any]] = []
    for run_file in sorted(runs_dir.glob("*.jsonl")):
        job_id = run_file.stem
        for line_index, raw in enumerate(run_file.read_text(encoding="utf-8").splitlines(), start=1):
            line = raw.strip()
            if not line:
                continue

            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue

            if not isinstance(row, dict):
                continue
            if row.get("action") != "finished":
                continue

            session_id = row.get("sessionId")
            if not isinstance(session_id, str) or not session_id:
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

            run_key = normalize_run_key("cron", job_id=job_id, session_id=session_id)
            if run_key is None:
                continue

            terminal_type = normalize_terminal_event_type(row.get("status") or row.get("result") or "finished")
            payload = {
                "jobId": job_id,
                "sessionId": session_id,
                "status": terminal_type,
            }
            events.append(
                build_event(
                    run_key=run_key,
                    event_type=terminal_type,
                    event_at_ms=event_at_ms,
                    source="cron-runs",
                    source_offset=f"{run_file.name}:{line_index}",
                    payload=payload,
                )
            )

    return events


def collect_subagent_events(subagent_file: Path) -> List[Dict[str, Any]]:
    doc = read_json(subagent_file)
    if not isinstance(doc, dict):
        return []

    runs = doc.get("runs")
    if not isinstance(runs, dict):
        return []

    events: List[Dict[str, Any]] = []
    for run_id, entry in sorted(runs.items(), key=lambda item: str(item[0])):
        if not isinstance(run_id, str) or not isinstance(entry, dict):
            continue

        run_key = normalize_run_key("subagent", run_id=run_id)
        if run_key is None:
            continue

        started_at_ms = parse_timestamp_ms(entry.get("startedAt")) or parse_timestamp_ms(entry.get("createdAt"))
        if started_at_ms is None:
            continue

        label = str(entry.get("label") or "Background task")
        child_session_key = entry.get("childSessionKey")
        session_key = child_session_key if isinstance(child_session_key, str) and child_session_key else f"subagent:{run_id}"
        payload = {
            "jobId": f"subagent:{run_id}",
            "jobName": label,
            "summary": label,
            "sessionId": session_key,
            "sessionKey": session_key,
            "startedAtMs": started_at_ms,
            "lastSeenAtMs": parse_timestamp_ms(entry.get("updatedAt")) or started_at_ms,
            "activityType": "subagent",
            "model": normalize_runtime_model(entry.get("model") or entry.get("agentModel")),
            "thinking": normalize_runtime_thinking(entry.get("thinking")),
        }

        events.append(
            build_event(
                run_key=run_key,
                event_type="started",
                event_at_ms=started_at_ms,
                source="subagent-registry",
                source_offset=f"subagent:{run_id}:started",
                payload=payload,
            )
        )

        heartbeat_at_ms = parse_timestamp_ms(entry.get("updatedAt")) or started_at_ms
        events.append(
            build_event(
                run_key=run_key,
                event_type="heartbeat",
                event_at_ms=heartbeat_at_ms,
                source="subagent-registry",
                source_offset=f"subagent:{run_id}:heartbeat",
                payload=payload,
            )
        )

        ended_at_ms = parse_timestamp_ms(entry.get("endedAt"))
        if ended_at_ms is not None:
            terminal_type = normalize_terminal_event_type(entry.get("status") or entry.get("endStatus") or "finished")
            events.append(
                build_event(
                    run_key=run_key,
                    event_type=terminal_type,
                    event_at_ms=ended_at_ms,
                    source="subagent-registry",
                    source_offset=f"subagent:{run_id}:ended",
                    payload={
                        "jobId": f"subagent:{run_id}",
                        "sessionId": session_key,
                        "status": terminal_type,
                    },
                )
            )

    return events


def load_existing_event_ids(events_file: Path) -> Set[str]:
    if not events_file.exists():
        return set()

    ids: Set[str] = set()
    for raw in events_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(row, dict):
            continue
        event_id = row.get("eventId")
        if isinstance(event_id, str) and event_id:
            ids.add(event_id)
    return ids


def collect_events(
    *,
    jobs_file: Path,
    sessions_file: Path,
    runs_dir: Path,
    subagent_file: Path,
) -> List[Dict[str, Any]]:
    jobs_by_id = load_jobs(jobs_file)
    return sort_events(
        collect_session_events(sessions_file, jobs_by_id)
        + collect_cron_terminal_events(runs_dir)
        + collect_subagent_events(subagent_file)
    )


def append_new_events(events_file: Path, events: Iterable[Dict[str, Any]]) -> int:
    existing_ids = load_existing_event_ids(events_file)
    new_events: List[Dict[str, Any]] = []

    for event in events:
        event_id = event.get("eventId")
        if not isinstance(event_id, str) or not event_id:
            continue
        if event_id in existing_ids:
            continue
        existing_ids.add(event_id)
        new_events.append(event)

    if not new_events:
        return 0

    events_file.parent.mkdir(parents=True, exist_ok=True)
    with events_file.open("a", encoding="utf-8") as handle:
        for event in new_events:
            handle.write(json.dumps(event, sort_keys=True) + "\n")

    return len(new_events)


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect runtime lifecycle events into runtime-events journal")
    parser.add_argument("--jobs-file", default="/Users/seankudrna/.openclaw/cron/jobs.json")
    parser.add_argument("--sessions-file", default="/Users/seankudrna/.openclaw/agents/main/sessions/sessions.json")
    parser.add_argument("--runs-dir", default="/Users/seankudrna/.openclaw/cron/runs")
    parser.add_argument("--subagent-file", default="/Users/seankudrna/.openclaw/subagents/runs.json")
    parser.add_argument("--events-file", default="/Users/seankudrna/.openclaw/workspace/status/runtime-events.jsonl")
    args = parser.parse_args()

    events = collect_events(
        jobs_file=Path(args.jobs_file),
        sessions_file=Path(args.sessions_file),
        runs_dir=Path(args.runs_dir),
        subagent_file=Path(args.subagent_file),
    )
    appended = append_new_events(Path(args.events_file), events)
    print(f"runtime events: collected={len(events)} appended={appended}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
