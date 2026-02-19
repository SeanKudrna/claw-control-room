#!/usr/bin/env python3
"""End-to-end smoke test for control-room MCP scaffold server."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.mcp.run_control_room_mcp_flow import run_flow


class ControlRoomMcpFlowTests(unittest.TestCase):
    def test_e2e_runtime_and_release_calls(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "proof.json"
            proof = run_flow(out)

            self.assertTrue(proof.get("ok"))
            listed = proof.get("tools", {}).get("listed", [])
            self.assertIn("control-room.runtime.materialize", listed)
            self.assertIn("control-room.release.extract-notes", listed)

            runtime_state = proof.get("runtimeState", {})
            self.assertEqual(runtime_state.get("status"), "running")
            self.assertEqual(runtime_state.get("activeCount"), 1)
            self.assertIsInstance(runtime_state.get("revision"), str)

            parsed = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(parsed.get("runtimeState", {}).get("activeCount"), 1)


if __name__ == "__main__":
    unittest.main()
