#!/usr/bin/env python3
"""Basic tests for control-room status builder helpers."""

from __future__ import annotations

import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path

# Ensure repo root import path.
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.lib.status_builder import (
    build_payload,
    parse_daily_plan_blocks,
    parse_today_status,
    parse_workstream,
    recent_activity,
    resolve_active_work,
    runtime_activity,
)


class StatusBuilderTests(unittest.TestCase):
    def test_parse_daily_plan_blocks(self) -> None:
        md = """
### 13:20-13:45 — Midday reliability + queue reconciliation
- Task:
  - Do thing
"""
        blocks = parse_daily_plan_blocks(md)
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0]["time"], "13:20-13:45")
        self.assertIn("Midday reliability", blocks[0]["task"])

    def test_parse_today_status(self) -> None:
        md = """
- Primary focus: reliability first
- Running now: 13:20-13:45 — queue cleanup
"""
        parsed = parse_today_status(md)
        self.assertEqual(parsed["currentFocus"], "reliability first")
        self.assertIn("queue cleanup", parsed["activeWork"])

    def test_parse_workstream(self) -> None:
        md = """
## Next 3 meaningful blocks
- Block A
- Block B

## Last completed with proof
- Completed one
- Proof: command passed
"""
        now_local = dt.datetime.now().replace(hour=15, minute=30)
        timeline = [{"time": "15:10-16:05", "task": "Reliability deep-work block B"}]

        stream = parse_workstream(md, timeline=timeline, active_work="", now_local=now_local)
        self.assertIn("15:10-16:05", stream["now"][0])
        self.assertIn("Block A", stream["next"][0])
        self.assertIn("Completed one", stream["done"][0])

    def test_parse_workstream_filters_past_next_items(self) -> None:
        md = """
## Next 3 meaningful blocks
- 14:30-15:15 — stale next block
- 17:00-17:10 — valid future block
"""
        now_local = dt.datetime.now().replace(hour=15, minute=30)
        timeline = [{"time": "15:10-16:05", "task": "Reliability deep-work block B"}]

        stream = parse_workstream(md, timeline=timeline, active_work="", now_local=now_local)
        joined = "\n".join(stream["next"])
        self.assertNotIn("14:30-15:15", joined)
        self.assertIn("17:00-17:10", joined)

    def test_resolve_active_work_stale_fallback(self) -> None:
        now_local = dt.datetime.now().replace(hour=15, minute=30)
        timeline = [{"time": "15:10-16:05", "task": "Reliability deep-work block B"}]

        resolved = resolve_active_work(
            raw_active_work="14:15-14:30 — stale block",
            timeline=timeline,
            now_local=now_local,
        )
        self.assertIn("15:10-16:05", resolved)

    def test_recent_activity(self) -> None:
        md = """
## 15:10 dashboard modernization
- Refactored control room to React + TypeScript
- Updated changelog and architecture docs
"""
        activity = recent_activity(md)
        self.assertGreaterEqual(len(activity), 2)
        self.assertEqual(activity[-1]["time"], "15:10")
        self.assertIn(activity[-1]["category"], {"ui", "docs", "ops"})

    def test_runtime_activity_detects_active_runs(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jobs_file = root / "jobs.json"
            sessions_file = root / "sessions.json"
            runs_dir = root / "runs"
            runs_dir.mkdir(parents=True, exist_ok=True)

            jobs_file.write_text(
                json.dumps(
                    {
                        "jobs": [
                            {"id": "job-1", "name": "Job One", "enabled": True},
                        ]
                    }
                ),
                encoding="utf-8",
            )

            now_ms = int(dt.datetime.now(dt.timezone.utc).timestamp() * 1000)
            sessions_file.write_text(
                json.dumps(
                    {
                        "agent:main:cron:job-1:run:session-finished": {
                            "sessionId": "session-finished",
                            "updatedAt": now_ms - 30_000,
                        },
                        "agent:main:cron:job-1:run:session-active": {
                            "sessionId": "session-active",
                            "updatedAt": now_ms - 12_000,
                        },
                    }
                ),
                encoding="utf-8",
            )

            (runs_dir / "job-1.jsonl").write_text(
                json.dumps(
                    {
                        "action": "finished",
                        "sessionId": "session-finished",
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            runtime = runtime_activity(jobs_file, sessions_file, runs_dir)
            self.assertEqual(runtime["status"], "running")
            self.assertEqual(runtime["activeCount"], 1)
            self.assertEqual(runtime["activeRuns"][0]["sessionId"], "session-active")
            self.assertEqual(runtime["activeRuns"][0]["jobName"], "Job One")

    def test_runtime_activity_excludes_status_publish_job(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jobs_file = root / "jobs.json"
            sessions_file = root / "sessions.json"
            runs_dir = root / "runs"
            runs_dir.mkdir(parents=True, exist_ok=True)

            jobs_file.write_text(
                json.dumps(
                    {
                        "jobs": [
                            {
                                "id": "job-publish",
                                "name": "Control room status publish (gist backend)",
                                "enabled": True,
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )

            now_ms = int(dt.datetime.now(dt.timezone.utc).timestamp() * 1000)
            sessions_file.write_text(
                json.dumps(
                    {
                        "agent:main:cron:job-publish:run:session-active": {
                            "sessionId": "session-active",
                            "updatedAt": now_ms - 10_000,
                        },
                    }
                ),
                encoding="utf-8",
            )

            runtime = runtime_activity(jobs_file, sessions_file, runs_dir)
            self.assertEqual(runtime["status"], "idle")
            self.assertEqual(runtime["activeCount"], 0)

    def test_build_payload_shape(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            (workspace / "memory").mkdir(parents=True, exist_ok=True)

            now_local = dt.datetime.now()
            start = (now_local - dt.timedelta(minutes=5)).strftime("%H:%M")
            end = (now_local + dt.timedelta(minutes=25)).strftime("%H:%M")

            (workspace / "DAILY_PLAN.md").write_text(
                f"### {start}-{end} — Live sample block\n", encoding="utf-8"
            )
            (workspace / "TODAY_STATUS.md").write_text(
                """
- Running now: 01:00-01:10 — stale block

## Next 3 meaningful blocks
- Next block

## Last completed with proof
- Done block
""",
                encoding="utf-8",
            )

            today_name = dt.datetime.now().strftime("%Y-%m-%d")
            (workspace / "memory" / f"{today_name}.md").write_text(
                "- sample finding\n", encoding="utf-8"
            )

            jobs_file = workspace / "jobs.json"
            jobs_file.write_text(
                json.dumps(
                    {
                        "jobs": [
                            {
                                "name": "Sample Job",
                                "enabled": True,
                                "state": {
                                    "nextRunAtMs": 2000000000000,
                                    "lastRunAtMs": 1999999999000,
                                    "lastStatus": "ok",
                                },
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            payload = build_payload(workspace, jobs_file)
            self.assertIn("generatedAt", payload)
            self.assertIn("timeline", payload)
            self.assertIn("nextJobs", payload)
            self.assertIn("reliability", payload)
            self.assertIn("controlRoomVersion", payload)
            self.assertIn("workstream", payload)
            self.assertIn("charts", payload)
            self.assertIn("activity", payload)
            self.assertIn("runtime", payload)
            self.assertIn("Live sample block", payload["currentFocus"])
            self.assertIn("Live sample block", payload["workstream"]["now"][0])


if __name__ == "__main__":
    unittest.main()
