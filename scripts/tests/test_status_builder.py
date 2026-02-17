#!/usr/bin/env python3
"""Basic tests for control-room status builder helpers."""

from __future__ import annotations

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

    def test_build_payload_shape(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            (workspace / "memory").mkdir(parents=True, exist_ok=True)
            (workspace / "DAILY_PLAN.md").write_text(
                "### 10:00-10:30 — Sample block\n", encoding="utf-8"
            )
            (workspace / "TODAY_STATUS.md").write_text(
                "- Primary focus: sample\n- Running now: test block\n", encoding="utf-8"
            )
            (workspace / "memory" / "2099-01-01.md").write_text("- sample finding\n", encoding="utf-8")

            jobs_file = workspace / "jobs.json"
            jobs_file.write_text(
                json.dumps(
                    {
                        "jobs": [
                            {
                                "name": "Sample Job",
                                "enabled": True,
                                "state": {"nextRunAtMs": 2000000000000},
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


if __name__ == "__main__":
    unittest.main()
