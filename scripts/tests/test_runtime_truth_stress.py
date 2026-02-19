#!/usr/bin/env python3
"""Deterministic stress checks for runtime truth replay."""

from __future__ import annotations

import random
import unittest
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.lib.runtime_events import build_event
from scripts.runtime.materialize_runtime_state import reduce_events


class RuntimeTruthStressTests(unittest.TestCase):
    def test_replay_is_deterministic_under_event_shuffle(self) -> None:
        now_ms = 20_000_000
        events = []
        for index in range(20):
            run_key = f"cron:job-{index}:session-{index}"
            start_ms = now_ms - (index + 1) * 10_000
            events.append(
                build_event(
                    run_key=run_key,
                    event_type="started",
                    event_at_ms=start_ms,
                    source="sessions-store",
                    source_offset=f"sessions:{index}",
                    payload={
                        "jobId": f"job-{index}",
                        "jobName": f"Job {index}",
                        "sessionId": f"session-{index}",
                        "sessionKey": f"agent:main:cron:job-{index}:run:session-{index}",
                        "summary": f"Job {index}",
                        "startedAtMs": start_ms,
                        "lastSeenAtMs": start_ms,
                        "activityType": "cron",
                    },
                )
            )

            if index % 2 == 0:
                events.append(
                    build_event(
                        run_key=run_key,
                        event_type="finished",
                        event_at_ms=start_ms + 2_000,
                        source="cron-runs",
                        source_offset=f"runs:{index}",
                        payload={"jobId": f"job-{index}", "sessionId": f"session-{index}", "status": "finished"},
                    )
                )

        baseline_active, _, _ = reduce_events(events, now_ms=now_ms, stale_ms=60_000)
        baseline_keys = [row["runKey"] for row in baseline_active]

        for seed in range(10):
            shuffled = list(events)
            random.Random(seed).shuffle(shuffled)
            active, _, _ = reduce_events(shuffled, now_ms=now_ms, stale_ms=60_000)
            self.assertEqual([row["runKey"] for row in active], baseline_keys)


if __name__ == "__main__":
    unittest.main()
