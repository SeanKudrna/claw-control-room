#!/usr/bin/env python3
"""Run an end-to-end MCP flow against the control-room scaffold server.

Flow:
1) initialize handshake
2) list tools
3) call runtime materialization tool on synthetic event stream
4) call release notes extraction tool
5) write proof artifact JSON
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict

import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.lib.runtime_events import build_event  # type: ignore
from scripts.mcp.jsonrpc_stdio import read_message, write_message  # type: ignore


def _send(proc: subprocess.Popen[bytes], payload: Dict[str, Any]) -> None:
    if proc.stdin is None:
        raise RuntimeError("missing stdin pipe")
    write_message(proc.stdin, payload)


def _recv(proc: subprocess.Popen[bytes]) -> Dict[str, Any]:
    if proc.stdout is None:
        raise RuntimeError("missing stdout pipe")
    message = read_message(proc.stdout)
    if message is None:
        raise RuntimeError("server closed stream unexpectedly")
    return message


def _call(proc: subprocess.Popen[bytes], request_id: int, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
    _send(
        proc,
        {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params,
        },
    )
    response = _recv(proc)
    if response.get("id") != request_id:
        raise RuntimeError(f"unexpected response id: {response}")
    if "error" in response:
        raise RuntimeError(f"json-rpc error: {response['error']}")
    result = response.get("result")
    if not isinstance(result, dict):
        raise RuntimeError(f"invalid result payload: {response}")
    return result


def run_flow(proof_out: Path) -> Dict[str, Any]:
    server_cmd = ["python3", str(ROOT / "scripts/mcp/control_room_mcp_server.py")]
    with tempfile.TemporaryDirectory() as td:
        temp = Path(td)
        events_file = temp / "runtime-events.jsonl"
        runtime_out = temp / "runtime-state.json"

        now_ms = int(dt.datetime.now(dt.timezone.utc).timestamp() * 1000)
        run_key = "cron:demo-job:session-1"
        event = build_event(
            run_key=run_key,
            event_type="started",
            event_at_ms=now_ms - 15_000,
            source="sessions-store",
            source_offset="demo:1",
            payload={
                "jobId": "demo-job",
                "jobName": "MCP runtime demo",
                "sessionId": "session-1",
                "sessionKey": "agent:main:cron:demo-job:run:session-1",
                "summary": "MCP runtime demo",
                "startedAtMs": now_ms - 15_000,
                "lastSeenAtMs": now_ms - 15_000,
                "activityType": "cron",
                "model": "openai-codex/gpt-5.3-codex",
                "thinking": "high",
            },
        )
        events_file.write_text(json.dumps(event) + "\n", encoding="utf-8")

        proc = subprocess.Popen(
            server_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        try:
            init = _call(
                proc,
                1,
                "initialize",
                {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {"tools": {}},
                    "clientInfo": {"name": "mcp-flow-runner", "version": "0.1.0"},
                },
            )

            _send(proc, {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})

            tools = _call(proc, 2, "tools/list", {})
            tool_names = [tool.get("name") for tool in tools.get("tools", []) if isinstance(tool, dict)]

            runtime_result = _call(
                proc,
                3,
                "tools/call",
                {
                    "name": "control-room.runtime.materialize",
                    "arguments": {
                        "eventsFile": str(events_file),
                        "out": str(runtime_out),
                        "nowMs": now_ms,
                    },
                },
            )

            release_result = _call(
                proc,
                4,
                "tools/call",
                {
                    "name": "control-room.release.extract-notes",
                    "arguments": {
                        "version": "1.4.38",
                        "changelog": str(ROOT / "CHANGELOG.md"),
                    },
                },
            )

            shutdown = _call(proc, 5, "shutdown", {})

        finally:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=2)

            if proc.stdin is not None:
                proc.stdin.close()
            if proc.stdout is not None:
                proc.stdout.close()
            if proc.stderr is not None:
                proc.stderr.close()

        runtime_state = json.loads(runtime_out.read_text(encoding="utf-8"))

        proof = {
            "ok": True,
            "timestamp": dt.datetime.now().astimezone().isoformat(),
            "server": {
                "command": server_cmd,
                "initialize": init,
                "shutdown": shutdown,
            },
            "tools": {
                "listed": tool_names,
                "runtimeCall": runtime_result,
                "releaseCall": release_result,
            },
            "runtimeState": {
                "path": str(runtime_out),
                "status": runtime_state.get("status"),
                "activeCount": runtime_state.get("activeCount"),
                "revision": runtime_state.get("revision"),
            },
        }

    proof_out.parent.mkdir(parents=True, exist_ok=True)
    proof_out.write_text(json.dumps(proof, indent=2) + "\n", encoding="utf-8")
    return proof


def main() -> int:
    parser = argparse.ArgumentParser(description="Run control-room MCP scaffold e2e flow")
    parser.add_argument(
        "--out",
        default="/Users/seankudrna/.openclaw/workspace/status/overnight/mcp-control-room-flow-proof.json",
    )
    args = parser.parse_args()

    proof = run_flow(Path(args.out))
    print(json.dumps({"ok": True, "out": args.out, "revision": proof["runtimeState"]["revision"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
