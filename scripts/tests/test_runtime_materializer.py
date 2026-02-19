#!/usr/bin/env python3
"""Tests for runtime event materialization."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.lib.runtime_events import build_event
from scripts.runtime.materialize_runtime_state import materialize_runtime_state, reduce_events


class RuntimeMaterializerTests(unittest.TestCase):
    def test_reduce_events_start_then_finish_removes_run(self) -> None:
        now_ms = 2_000_000
        run_key = "cron:job-1:session-a"
        events = [
            build_event(
                run_key=run_key,
                event_type="started",
                event_at_ms=now_ms - 20_000,
                source="sessions-store",
                source_offset="sessions:1",
                payload={
                    "jobId": "job-1",
                    "jobName": "Job One",
                    "sessionId": "session-a",
                    "sessionKey": "agent:main:cron:job-1:run:session-a",
                    "summary": "Job One",
                    "startedAtMs": now_ms - 20_000,
                    "lastSeenAtMs": now_ms - 20_000,
                    "activityType": "cron",
                },
            ),
            build_event(
                run_key=run_key,
                event_type="finished",
                event_at_ms=now_ms - 10_000,
                source="cron-runs",
                source_offset="job-1.jsonl:1",
                payload={"jobId": "job-1", "sessionId": "session-a", "status": "finished"},
            ),
        ]

        active, terminals, dropped_stale = reduce_events(events, now_ms=now_ms, stale_ms=60_000)
        self.assertEqual(active, [])
        self.assertIn(run_key, terminals)
        self.assertEqual(dropped_stale, 0)

    def test_reduce_events_stale_expiry(self) -> None:
        now_ms = 5_000_000
        run_key = "subagent:run-1"
        events = [
            build_event(
                run_key=run_key,
                event_type="started",
                event_at_ms=now_ms - 200_000,
                source="subagent-registry",
                source_offset="subagent:run-1:started",
                payload={
                    "jobId": "subagent:run-1",
                    "jobName": "Background task",
                    "sessionId": "agent:main:subagent:abc",
                    "sessionKey": "agent:main:subagent:abc",
                    "summary": "Background task",
                    "startedAtMs": now_ms - 200_000,
                    "lastSeenAtMs": now_ms - 200_000,
                    "activityType": "subagent",
                },
            ),
        ]

        active, terminals, dropped_stale = reduce_events(events, now_ms=now_ms, stale_ms=60_000)
        self.assertEqual(active, [])
        self.assertIn(run_key, terminals)
        self.assertEqual(terminals[run_key]["eventType"], "stale_expired")
        self.assertEqual(dropped_stale, 1)

    def test_reduce_events_preserves_model_and_thinking(self) -> None:
        now_ms = 6_000_000
        run_key = "cron:job-2:session-b"
        events = [
            build_event(
                run_key=run_key,
                event_type="heartbeat",
                event_at_ms=now_ms - 15_000,
                source="sessions-store",
                source_offset="sessions:2",
                payload={
                    "jobId": "job-2",
                    "jobName": "Model Rich Job",
                    "sessionId": "session-b",
                    "sessionKey": "agent:main:cron:job-2:run:session-b",
                    "summary": "Model Rich Job",
                    "startedAtMs": now_ms - 20_000,
                    "lastSeenAtMs": now_ms - 15_000,
                    "activityType": "cron",
                    "model": "openai-codex/gpt-5.3-codex",
                    "thinking": "high",
                },
            ),
        ]

        active, _, dropped_stale = reduce_events(events, now_ms=now_ms, stale_ms=60_000)
        self.assertEqual(dropped_stale, 0)
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0]["model"], "openai-codex/gpt-5.3-codex")
        self.assertEqual(active[0]["thinking"], "high")

    def test_materialize_runtime_state_revision_monotonic(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            events_file = root / "runtime-events.jsonl"
            state_file = root / "runtime-state.json"

            now_ms = 8_000_000
            event = build_event(
                run_key="cron:job-1:session-a",
                event_type="started",
                event_at_ms=now_ms - 5_000,
                source="sessions-store",
                source_offset="sessions:1",
                payload={
                    "jobId": "job-1",
                    "jobName": "Job One",
                    "sessionId": "session-a",
                    "sessionKey": "agent:main:cron:job-1:run:session-a",
                    "summary": "Job One",
                    "startedAtMs": now_ms - 5_000,
                    "lastSeenAtMs": now_ms - 5_000,
                    "activityType": "cron",
                },
            )
            events_file.write_text(json.dumps(event) + "\n", encoding="utf-8")

            first = materialize_runtime_state(
                events_file=events_file,
                runtime_state_file=state_file,
                now_ms=now_ms,
                stale_ms=60_000,
            )
            second = materialize_runtime_state(
                events_file=events_file,
                runtime_state_file=state_file,
                now_ms=now_ms + 1_000,
                stale_ms=60_000,
            )

            self.assertNotEqual(first["revision"], second["revision"])
            self.assertEqual(first["activeCount"], 1)
            self.assertEqual(second["activeCount"], 1)


if __name__ == "__main__":
    unittest.main()
