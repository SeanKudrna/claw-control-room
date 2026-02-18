#!/usr/bin/env python3
"""Basic tests for control-room status builder helpers."""

from __future__ import annotations

import datetime as dt
import json
import os
import tempfile
import unittest
from pathlib import Path

# Ensure repo root import path.
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.lib.status_builder import (
    SKILL_CATALOG,
    SKILL_MAX_TIER,
    build_payload,
    build_skills_payload,
    build_workstream_lanes,
    parse_daily_plan_blocks,
    parse_today_status,
    recent_activity,
    resolve_active_work,
    runtime_activity,
    sanitize_payload_for_static_snapshot,
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

    def test_workstream_running_activity_precedence(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jobs_file = root / "jobs.json"
            jobs_file.write_text(json.dumps({"jobs": []}), encoding="utf-8")
            state_path = root / "workstream-state.json"

            now_local = dt.datetime(2026, 2, 18, 8, 0)
            timeline = [{"time": "08:05-08:30", "task": "Morning timeline block"}]
            runtime = {
                "activeRuns": [
                    {
                        "sessionId": "run-1",
                        "summary": "Active subagent task",
                        "startedAtMs": int(dt.datetime(2026, 2, 18, 7, 58, tzinfo=dt.timezone.utc).timestamp() * 1000),
                    }
                ]
            }

            lanes = build_workstream_lanes(timeline, jobs_file, runtime, now_local, state_path)
            self.assertEqual(lanes["now"], ["Active subagent task"])

    def test_workstream_no_running_falls_back_to_earliest_upcoming(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jobs_file = root / "jobs.json"
            local_tz = dt.datetime.now().astimezone().tzinfo
            next_run_ms = int(dt.datetime(2026, 2, 18, 8, 15, tzinfo=local_tz).astimezone(dt.timezone.utc).timestamp() * 1000)
            jobs_file.write_text(
                json.dumps(
                    {
                        "jobs": [
                            {
                                "id": "job-1",
                                "name": "Soon job",
                                "enabled": True,
                                "state": {"nextRunAtMs": next_run_ms},
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            state_path = root / "workstream-state.json"
            now_local = dt.datetime(2026, 2, 18, 7, 30)
            timeline = [{"time": "09:00-09:30", "task": "Later timeline block"}]

            lanes = build_workstream_lanes(timeline, jobs_file, {"activeRuns": []}, now_local, state_path)
            self.assertIn("Scheduled job: Soon job", lanes["now"][0])

    def test_workstream_next_ordering_after_now(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jobs_file = root / "jobs.json"
            jobs_file.write_text(
                json.dumps(
                    {
                        "jobs": [
                            {
                                "id": "job-1",
                                "name": "Second event",
                                "enabled": True,
                                "state": {
                                    "nextRunAtMs": int(dt.datetime(2026, 2, 18, 8, 20, tzinfo=dt.datetime.now().astimezone().tzinfo).astimezone(dt.timezone.utc).timestamp() * 1000)
                                },
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            state_path = root / "workstream-state.json"
            now_local = dt.datetime(2026, 2, 18, 8, 0)
            timeline = [
                {"time": "08:05-08:10", "task": "First event"},
                {"time": "08:30-08:45", "task": "Third event"},
            ]

            lanes = build_workstream_lanes(timeline, jobs_file, {"activeRuns": []}, now_local, state_path)
            self.assertIn("08:05-08:10", lanes["now"][0])
            self.assertIn("Scheduled job: Second event", lanes["next"][0])
            self.assertIn("08:30-08:45", lanes["next"][1])

    def test_workstream_done_day_reset_and_transition(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jobs_file = root / "jobs.json"
            jobs_file.write_text(json.dumps({"jobs": []}), encoding="utf-8")
            state_path = root / "workstream-state.json"
            timeline = [{"time": "08:05-08:10", "task": "Transition block"}]

            first_now = dt.datetime(2026, 2, 18, 8, 0)
            lanes_first = build_workstream_lanes(timeline, jobs_file, {"activeRuns": []}, first_now, state_path)
            self.assertEqual(lanes_first["done"], [])

            second_now = dt.datetime(2026, 2, 18, 8, 20)
            lanes_second = build_workstream_lanes([], jobs_file, {"activeRuns": []}, second_now, state_path)
            self.assertEqual(lanes_second["done"][0], "08:10 — Transition block")

            third_now = dt.datetime(2026, 2, 19, 8, 0)
            lanes_third = build_workstream_lanes([], jobs_file, {"activeRuns": []}, third_now, state_path)
            self.assertEqual(lanes_third["done"], [])

    def test_workstream_timeline_block_lifecycle_pre_start_in_progress_post_end(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jobs_file = root / "jobs.json"
            jobs_file.write_text(json.dumps({"jobs": []}), encoding="utf-8")
            state_path = root / "workstream-state.json"
            timeline = [{"time": "08:05-08:20", "task": "Lifecycle block"}]

            pre_start = dt.datetime(2026, 2, 18, 8, 0)
            lanes_pre = build_workstream_lanes(timeline, jobs_file, {"activeRuns": []}, pre_start, state_path)
            self.assertIn("08:05-08:20", lanes_pre["now"][0])
            self.assertEqual(lanes_pre["done"], [])

            in_progress = dt.datetime(2026, 2, 18, 8, 10)
            lanes_in_progress = build_workstream_lanes(timeline, jobs_file, {"activeRuns": []}, in_progress, state_path)
            self.assertIn("08:05-08:20", lanes_in_progress["now"][0])
            self.assertEqual(lanes_in_progress["done"], [])

            post_end = dt.datetime(2026, 2, 18, 8, 25)
            lanes_post = build_workstream_lanes(timeline, jobs_file, {"activeRuns": []}, post_end, state_path)
            self.assertEqual(lanes_post["now"], [])
            self.assertIn("08:20 — Lifecycle block", lanes_post["done"][0])

    def test_workstream_done_order_is_newest_first(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jobs_file = root / "jobs.json"
            jobs_file.write_text(json.dumps({"jobs": []}), encoding="utf-8")
            state_path = root / "workstream-state.json"

            first_timeline = [{"time": "08:00-08:05", "task": "First completed"}]
            first_now = dt.datetime(2026, 2, 18, 7, 59)
            build_workstream_lanes(first_timeline, jobs_file, {"activeRuns": []}, first_now, state_path)

            second_timeline = [{"time": "08:10-08:15", "task": "Second completed"}]
            second_now = dt.datetime(2026, 2, 18, 8, 9)
            build_workstream_lanes(second_timeline, jobs_file, {"activeRuns": []}, second_now, state_path)

            after_second = dt.datetime(2026, 2, 18, 8, 20)
            lanes = build_workstream_lanes([], jobs_file, {"activeRuns": []}, after_second, state_path)

            self.assertEqual(len(lanes["done"]), 2)
            self.assertEqual(lanes["done"][0], "08:15 — Second completed")
            self.assertEqual(lanes["done"][1], "08:05 — First completed")

    def test_workstream_done_format_keeps_items_without_derivable_time(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jobs_file = root / "jobs.json"
            jobs_file.write_text(json.dumps({"jobs": []}), encoding="utf-8")
            state_path = root / "workstream-state.json"
            now_local = dt.datetime(2026, 2, 18, 8, 20)
            state_path.write_text(
                json.dumps(
                    {
                        "day": now_local.strftime("%Y-%m-%d"),
                        "seenNow": [],
                        "done": ["manual:1"],
                        "labels": {"manual:1": "Unscheduled follow-up complete"},
                    }
                ),
                encoding="utf-8",
            )

            lanes = build_workstream_lanes([], jobs_file, {"activeRuns": []}, now_local, state_path)
            self.assertEqual(lanes["done"], ["Unscheduled follow-up complete"])

    def test_workstream_now_next_never_include_past(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jobs_file = root / "jobs.json"
            past_job_ms = int(dt.datetime(2026, 2, 18, 7, 0, tzinfo=dt.datetime.now().astimezone().tzinfo).astimezone(dt.timezone.utc).timestamp() * 1000)
            jobs_file.write_text(
                json.dumps(
                    {
                        "jobs": [
                            {
                                "id": "job-past",
                                "name": "Past job",
                                "enabled": True,
                                "state": {"nextRunAtMs": past_job_ms},
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            state_path = root / "workstream-state.json"
            now_local = dt.datetime(2026, 2, 18, 8, 0)
            timeline = [{"time": "07:30-07:45", "task": "Past timeline"}]

            lanes = build_workstream_lanes(timeline, jobs_file, {"activeRuns": []}, now_local, state_path)
            self.assertEqual(lanes["now"], [])
            self.assertEqual(lanes["next"], [])

    def test_resolve_active_work_stale_fallback(self) -> None:
        now_local = dt.datetime.now().replace(hour=15, minute=30)
        timeline = [{"time": "15:10-16:05", "task": "Reliability deep-work block B"}]

        resolved = resolve_active_work(
            raw_active_work="14:15-14:30 — stale block",
            timeline=timeline,
            now_local=now_local,
        )
        self.assertIn("15:10-16:05", resolved)

    def test_resolve_active_work_stale_single_time_completed_item(self) -> None:
        now_local = dt.datetime.now().replace(hour=7, minute=45)
        timeline = [{"time": "13:20-13:45", "task": "Midday reliability + queue reconciliation"}]

        resolved = resolve_active_work(
            raw_active_work="01:00 downtime-guard reliability deep-work fallback (completed with fresh proof).",
            timeline=timeline,
            now_local=now_local,
        )
        self.assertIn("Next up:", resolved)
        self.assertIn("13:20-13:45", resolved)

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
            self.assertEqual(runtime["activeRuns"][0]["activityType"], "cron")

    def test_runtime_activity_detects_active_subagent_runs(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jobs_file = root / "jobs.json"
            sessions_file = root / "sessions.json"
            runs_dir = root / "runs"
            subagent_runs_file = root / "subagent-runs.json"
            runs_dir.mkdir(parents=True, exist_ok=True)

            jobs_file.write_text(json.dumps({"jobs": []}), encoding="utf-8")
            sessions_file.write_text(json.dumps({}), encoding="utf-8")

            now_ms = int(dt.datetime.now(dt.timezone.utc).timestamp() * 1000)
            subagent_runs_file.write_text(
                json.dumps(
                    {
                        "version": 2,
                        "runs": {
                            "run-1": {
                                "runId": "run-1",
                                "childSessionKey": "agent:main:subagent:abc123",
                                "label": "Investigate dashboard UX",
                                "createdAt": now_ms - 45_000,
                                "startedAt": now_ms - 40_000,
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )

            runtime = runtime_activity(
                jobs_file,
                sessions_store_path=sessions_file,
                runs_dir=runs_dir,
                subagent_registry_path=subagent_runs_file,
            )
            self.assertEqual(runtime["status"], "running")
            self.assertEqual(runtime["activeCount"], 1)
            self.assertEqual(runtime["activeRuns"][0]["activityType"], "subagent")
            self.assertIn("subagent:run-1", runtime["activeRuns"][0]["jobId"])

    def test_runtime_activity_ignores_ended_subagent_runs(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jobs_file = root / "jobs.json"
            sessions_file = root / "sessions.json"
            runs_dir = root / "runs"
            subagent_runs_file = root / "subagent-runs.json"
            runs_dir.mkdir(parents=True, exist_ok=True)

            jobs_file.write_text(json.dumps({"jobs": []}), encoding="utf-8")
            sessions_file.write_text(json.dumps({}), encoding="utf-8")

            now_ms = int(dt.datetime.now(dt.timezone.utc).timestamp() * 1000)
            subagent_runs_file.write_text(
                json.dumps(
                    {
                        "version": 2,
                        "runs": {
                            "run-1": {
                                "runId": "run-1",
                                "childSessionKey": "agent:main:subagent:abc123",
                                "label": "Ended task",
                                "createdAt": now_ms - 60_000,
                                "startedAt": now_ms - 55_000,
                                "endedAt": now_ms - 5_000,
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )

            runtime = runtime_activity(
                jobs_file,
                sessions_store_path=sessions_file,
                runs_dir=runs_dir,
                subagent_registry_path=subagent_runs_file,
            )
            self.assertEqual(runtime["status"], "idle")
            self.assertEqual(runtime["activeCount"], 0)

    def test_runtime_activity_subagent_label_uses_task_when_generic(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jobs_file = root / "jobs.json"
            sessions_file = root / "sessions.json"
            runs_dir = root / "runs"
            subagent_runs_file = root / "subagent-runs.json"
            runs_dir.mkdir(parents=True, exist_ok=True)

            jobs_file.write_text(json.dumps({"jobs": []}), encoding="utf-8")
            sessions_file.write_text(json.dumps({}), encoding="utf-8")

            now_ms = int(dt.datetime.now(dt.timezone.utc).timestamp() * 1000)
            subagent_runs_file.write_text(
                json.dumps(
                    {
                        "version": 2,
                        "runs": {
                            "run-1": {
                                "runId": "run-1",
                                "childSessionKey": "agent:main:subagent:abc123",
                                "label": "Background task",
                                "task": "Audit dashboard readability and ship visual hierarchy cleanup",
                                "createdAt": now_ms - 60_000,
                                "startedAt": now_ms - 58_000,
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )

            runtime = runtime_activity(
                jobs_file,
                sessions_store_path=sessions_file,
                runs_dir=runs_dir,
                subagent_registry_path=subagent_runs_file,
            )
            self.assertEqual(runtime["status"], "running")
            self.assertEqual(runtime["activeCount"], 1)
            self.assertIn("Audit dashboard readability", runtime["activeRuns"][0]["jobName"])
            self.assertEqual(runtime["activeRuns"][0]["sessionKey"], "agent:main:subagent:abc123")

    def test_runtime_activity_ignores_main_session_rows(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jobs_file = root / "jobs.json"
            sessions_file = root / "sessions.json"
            runs_dir = root / "runs"
            session_file = root / "main-session.jsonl"
            runs_dir.mkdir(parents=True, exist_ok=True)

            jobs_file.write_text(json.dumps({"jobs": []}), encoding="utf-8")

            now = dt.datetime.now(dt.timezone.utc)
            session_file.write_text(
                json.dumps(
                    {
                        "type": "message",
                        "timestamp": now.isoformat().replace("+00:00", "Z"),
                        "message": {
                            "role": "assistant",
                            "content": [
                                {
                                    "type": "toolCall",
                                    "name": "exec",
                                    "arguments": {"command": "echo hi"},
                                }
                            ],
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            sessions_file.write_text(
                json.dumps(
                    {
                        "agent:main:main": {
                            "sessionId": "main-session-id",
                            "sessionFile": str(session_file),
                            "updatedAt": int(now.timestamp() * 1000),
                        }
                    }
                ),
                encoding="utf-8",
            )

            runtime = runtime_activity(jobs_file, sessions_file, runs_dir)
            self.assertEqual(runtime["status"], "idle")
            self.assertEqual(runtime["activeCount"], 0)

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

    def test_build_skills_payload_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            (workspace / "memory").mkdir(parents=True, exist_ok=True)
            now_local = dt.datetime(2026, 2, 18, 9, 0)
            (workspace / "memory" / "2026-02-18.md").write_text(
                "- reliability watchdog and runtime scheduler updates\n- release changelog publish\n",
                encoding="utf-8",
            )
            (workspace / "ClawPrime_Memory.md").write_text(
                "memory evolution pattern reliability dashboard\n",
                encoding="utf-8",
            )

            payload_a = build_skills_payload(workspace, now_local)
            payload_b = build_skills_payload(workspace, now_local)

            self.assertEqual(payload_a["evolution"]["deterministicSeed"], payload_b["evolution"]["deterministicSeed"])
            self.assertEqual(len(payload_a["nodes"]), len(SKILL_CATALOG))
            self.assertIn("activeCount", payload_a)

            for node in payload_a["nodes"]:
                self.assertIn("currentTier", node)
                self.assertIn("maxTier", node)
                self.assertIn("tierLadder", node)
                self.assertEqual(node["maxTier"], SKILL_MAX_TIER)
                self.assertGreaterEqual(node["currentTier"], 0)
                self.assertLessEqual(node["currentTier"], SKILL_MAX_TIER)
                self.assertEqual(len(node["tierLadder"]), SKILL_MAX_TIER)
                self.assertEqual(node["tierLadder"][0]["tier"], 1)
                self.assertEqual(node["tierLadder"][-1]["tier"], SKILL_MAX_TIER)

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
            self.assertIn("skills", payload)
            self.assertIn("runtime", payload)
            self.assertIn("Live sample block", payload["currentFocus"])
            self.assertGreaterEqual(len(payload["workstream"]["now"]), 1)

    def test_sanitize_payload_for_static_snapshot_clears_runtime_runs(self) -> None:
        payload = {
            "runtime": {
                "status": "running",
                "isIdle": False,
                "activeCount": 2,
                "activeRuns": [
                    {"jobId": "job-1", "jobName": "Some task"},
                    {"jobId": "job-2", "jobName": "Other task"},
                ],
                "checkedAtMs": 123,
                "source": "cron-run reconciliation + subagent registry",
            },
            "other": "value",
        }

        sanitized = sanitize_payload_for_static_snapshot(payload)
        self.assertEqual(sanitized["runtime"]["status"], "idle")
        self.assertTrue(sanitized["runtime"]["isIdle"])
        self.assertEqual(sanitized["runtime"]["activeCount"], 0)
        self.assertEqual(sanitized["runtime"]["activeRuns"], [])
        self.assertIn("static fallback runtime sanitized", sanitized["runtime"]["source"])
        self.assertEqual(sanitized["other"], "value")


if __name__ == "__main__":
    unittest.main()
