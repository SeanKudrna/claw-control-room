#!/usr/bin/env python3
"""Tests for runtime reconciler start/finish/stale guarantees."""

from __future__ import annotations

import unittest
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.lib.runtime_reconciler import normalize_run_key, reconcile


class RuntimeReconcilerTests(unittest.TestCase):
    def test_normalize_run_key(self) -> None:
        self.assertEqual(
            normalize_run_key("cron", job_id="job-1", session_id="session-1"),
            "cron:job-1:session-1",
        )
        self.assertEqual(normalize_run_key("subagent", run_id="run-1"), "subagent:run-1")
        self.assertIsNone(normalize_run_key("cron", job_id="job-1"))

    def test_reconcile_terminal_event_removes_lingering_candidate(self) -> None:
        now_ms = 1_000_000
        result = reconcile(
            now_ms=now_ms,
            stale_ms=120_000,
            candidates=[
                {
                    "runKey": "cron:job-1:session-a",
                    "jobId": "job-1",
                    "jobName": "Job One",
                    "sessionId": "session-a",
                    "sessionKey": "agent:main:cron:job-1:run:session-a",
                    "summary": "Job One",
                    "startedAtMs": now_ms - 20_000,
                    "lastSeenAtMs": now_ms - 5_000,
                    "activityType": "cron",
                }
            ],
            terminal_events=[
                {
                    "runKey": "cron:job-1:session-a",
                    "eventType": "finished",
                    "eventAtMs": now_ms - 1_000,
                }
            ],
        )
        self.assertEqual(result["activeCount"], 0)
        self.assertEqual(result["droppedTerminalCount"], 1)

    def test_reconcile_drops_stale_orphans(self) -> None:
        now_ms = 5_000_000
        result = reconcile(
            now_ms=now_ms,
            stale_ms=60_000,
            candidates=[
                {
                    "runKey": "cron:job-1:session-stale",
                    "jobId": "job-1",
                    "jobName": "Stale Job",
                    "sessionId": "session-stale",
                    "sessionKey": "agent:main:cron:job-1:run:session-stale",
                    "summary": "Stale Job",
                    "startedAtMs": now_ms - 180_000,
                    "lastSeenAtMs": now_ms - 120_000,
                    "activityType": "cron",
                }
            ],
            terminal_events=[],
        )
        self.assertEqual(result["activeCount"], 0)
        self.assertEqual(result["droppedStaleCount"], 1)

    def test_reconcile_orders_runs_deterministically(self) -> None:
        now_ms = 9_000_000
        result = reconcile(
            now_ms=now_ms,
            stale_ms=120_000,
            candidates=[
                {
                    "runKey": "cron:job-2:session-b",
                    "jobId": "job-2",
                    "jobName": "Job Two",
                    "sessionId": "session-b",
                    "sessionKey": "agent:main:cron:job-2:run:session-b",
                    "summary": "Job Two",
                    "startedAtMs": now_ms - 30_000,
                    "lastSeenAtMs": now_ms - 1_000,
                    "activityType": "cron",
                },
                {
                    "runKey": "cron:job-1:session-a",
                    "jobId": "job-1",
                    "jobName": "Job One",
                    "sessionId": "session-a",
                    "sessionKey": "agent:main:cron:job-1:run:session-a",
                    "summary": "Job One",
                    "startedAtMs": now_ms - 30_000,
                    "lastSeenAtMs": now_ms - 1_500,
                    "activityType": "cron",
                },
            ],
            terminal_events=[],
        )
        self.assertEqual(result["activeCount"], 2)
        ordered = [row["runKey"] for row in result["activeRuns"]]
        self.assertEqual(ordered, ["cron:job-1:session-a", "cron:job-2:session-b"])


if __name__ == "__main__":
    unittest.main()
