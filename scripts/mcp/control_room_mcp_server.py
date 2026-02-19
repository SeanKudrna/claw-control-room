#!/usr/bin/env python3
"""Control-Room MCP scaffold server.

Provides issue/status/release/runtime actions over MCP tools.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Dict, Tuple

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_status_json import sanitize_payload_for_static_snapshot  # type: ignore
from scripts.extract_release_notes import extract_release_notes  # type: ignore
from scripts.issue_snapshot import render_markdown, run_gh_issue_list  # type: ignore
from scripts.lib.status_builder import build_payload  # type: ignore
from scripts.mcp.jsonrpc_stdio import (  # type: ignore
    ProtocolError,
    jsonrpc_error,
    jsonrpc_success,
    read_message,
    write_message,
)
from scripts.runtime.materialize_runtime_state import materialize_runtime_state  # type: ignore

SERVER_INFO = {
    "name": "control-room-mcp",
    "version": "0.1.0",
}

PROTOCOL_VERSION = "2025-03-26"

TOOL_DEFS = [
    {
        "name": "control-room.issue.snapshot",
        "description": "Fetch open GitHub issues and optionally write markdown snapshot.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo": {"type": "string"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 200},
                "out": {"type": "string"},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "control-room.status.build",
        "description": "Build a control-room status payload JSON snapshot.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspace": {"type": "string"},
                "jobsFile": {"type": "string"},
                "out": {"type": "string"},
                "liveRuntime": {"type": "boolean"},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "control-room.release.extract-notes",
        "description": "Extract release notes section for a semver from CHANGELOG.md.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "version": {"type": "string"},
                "changelog": {"type": "string"},
                "out": {"type": "string"},
            },
            "required": ["version"],
            "additionalProperties": False,
        },
    },
    {
        "name": "control-room.runtime.materialize",
        "description": "Replay runtime events journal into runtime-state materialized snapshot.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "eventsFile": {"type": "string"},
                "out": {"type": "string"},
                "staleMs": {"type": "integer", "minimum": 1000},
                "nowMs": {"type": "integer", "minimum": 1},
            },
            "additionalProperties": False,
        },
    },
]


def _tool_result(*, text: str, structured: Dict[str, Any], is_error: bool = False) -> Dict[str, Any]:
    return {
        "content": [{"type": "text", "text": text}],
        "structuredContent": structured,
        "isError": is_error,
    }


def _resolve_path(raw: str, default: Path) -> Path:
    if not raw:
        return default
    candidate = Path(raw)
    if candidate.is_absolute():
        return candidate
    return (ROOT / candidate).resolve()


def tool_issue_snapshot(arguments: Dict[str, Any]) -> Dict[str, Any]:
    repo = str(arguments.get("repo") or "SeanKudrna/claw-control-room")
    limit_raw = arguments.get("limit", 50)
    try:
        limit = int(limit_raw)
    except (TypeError, ValueError):
        limit = 50
    limit = max(1, min(200, limit))

    out_raw = arguments.get("out")
    out_path: Path | None = None
    if isinstance(out_raw, str) and out_raw.strip():
        out_path = _resolve_path(out_raw, ROOT / "status/issue-snapshot.md")

    issues = run_gh_issue_list(repo, limit)
    markdown = render_markdown(repo, issues)

    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(markdown + "\n", encoding="utf-8")

    return {
        "repo": repo,
        "openIssues": len(issues),
        "out": str(out_path) if out_path else "",
        "generatedAt": dt.datetime.now().astimezone().isoformat(),
    }


def tool_status_build(arguments: Dict[str, Any]) -> Dict[str, Any]:
    workspace = _resolve_path(
        str(arguments.get("workspace") or "/Users/seankudrna/.openclaw/workspace"),
        Path("/Users/seankudrna/.openclaw/workspace"),
    )
    jobs_file = _resolve_path(
        str(arguments.get("jobsFile") or "/Users/seankudrna/.openclaw/cron/jobs.json"),
        Path("/Users/seankudrna/.openclaw/cron/jobs.json"),
    )
    out = _resolve_path(
        str(arguments.get("out") or str(ROOT / "status/mcp-status.json")),
        ROOT / "status/mcp-status.json",
    )
    live_runtime = bool(arguments.get("liveRuntime", True))

    payload = build_payload(workspace, jobs_file)
    if not live_runtime:
        payload = sanitize_payload_for_static_snapshot(payload)

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    runtime = payload.get("runtime") if isinstance(payload, dict) else {}
    active_count = runtime.get("activeCount") if isinstance(runtime, dict) else 0
    runtime_status = runtime.get("status") if isinstance(runtime, dict) else "unknown"

    return {
        "out": str(out),
        "generatedAt": payload.get("generatedAt") if isinstance(payload, dict) else "",
        "runtimeStatus": runtime_status,
        "activeCount": active_count,
        "liveRuntime": live_runtime,
    }


def tool_release_extract(arguments: Dict[str, Any]) -> Dict[str, Any]:
    version = str(arguments.get("version") or "").strip()
    if not version:
        raise ValueError("version is required")

    changelog = _resolve_path(str(arguments.get("changelog") or "CHANGELOG.md"), ROOT / "CHANGELOG.md")
    out_raw = arguments.get("out")
    out_path: Path | None = None
    if isinstance(out_raw, str) and out_raw.strip():
        out_path = _resolve_path(out_raw, ROOT / f"status/release-notes-{version}.md")

    notes = extract_release_notes(changelog.read_text(encoding="utf-8"), version)

    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(notes, encoding="utf-8")

    return {
        "version": version,
        "changelog": str(changelog),
        "out": str(out_path) if out_path else "",
        "lines": len(notes.strip().splitlines()),
        "preview": "\n".join(notes.strip().splitlines()[:4]),
    }


def tool_runtime_materialize(arguments: Dict[str, Any]) -> Dict[str, Any]:
    events_file = _resolve_path(
        str(arguments.get("eventsFile") or "/Users/seankudrna/.openclaw/workspace/status/runtime-events.jsonl"),
        Path("/Users/seankudrna/.openclaw/workspace/status/runtime-events.jsonl"),
    )
    out = _resolve_path(
        str(arguments.get("out") or "/Users/seankudrna/.openclaw/workspace/status/runtime-state.json"),
        Path("/Users/seankudrna/.openclaw/workspace/status/runtime-state.json"),
    )
    stale_ms = int(arguments.get("staleMs", 10 * 60 * 1000))

    now_ms_raw = arguments.get("nowMs")
    now_ms = int(now_ms_raw) if now_ms_raw is not None else None

    runtime_state = materialize_runtime_state(
        events_file=events_file,
        runtime_state_file=out,
        now_ms=now_ms,
        stale_ms=stale_ms,
    )

    return {
        "out": str(out),
        "revision": runtime_state.get("revision"),
        "status": runtime_state.get("status"),
        "activeCount": runtime_state.get("activeCount"),
        "terminalCount": runtime_state.get("terminalCount"),
        "droppedStaleCount": runtime_state.get("droppedStaleCount"),
    }


TOOL_HANDLERS: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {
    "control-room.issue.snapshot": tool_issue_snapshot,
    "control-room.status.build": tool_status_build,
    "control-room.release.extract-notes": tool_release_extract,
    "control-room.runtime.materialize": tool_runtime_materialize,
}


def _handle_tools_call(params: Dict[str, Any]) -> Dict[str, Any]:
    name = params.get("name")
    args = params.get("arguments")

    if not isinstance(name, str) or not name:
        return _tool_result(
            text="tool call missing name",
            structured={"ok": False, "error": "tool call missing name"},
            is_error=True,
        )

    if not isinstance(args, dict):
        args = {}

    handler = TOOL_HANDLERS.get(name)
    if handler is None:
        return _tool_result(
            text=f"unknown tool: {name}",
            structured={"ok": False, "error": f"unknown tool: {name}"},
            is_error=True,
        )

    try:
        result = handler(args)
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError) as exc:
        return _tool_result(
            text=f"tool failed: {exc}",
            structured={"ok": False, "tool": name, "error": str(exc)},
            is_error=True,
        )
    except Exception as exc:  # pragma: no cover - safety net for ad-hoc runtime
        return _tool_result(
            text=f"tool failed unexpectedly: {exc}",
            structured={"ok": False, "tool": name, "error": str(exc)},
            is_error=True,
        )

    return _tool_result(
        text=f"ok: {name}",
        structured={"ok": True, "tool": name, "result": result},
    )


def _handle_request(message: Dict[str, Any]) -> Tuple[bool, Dict[str, Any] | None]:
    message_id = message.get("id")
    method = message.get("method")
    params = message.get("params") if isinstance(message.get("params"), dict) else {}

    if not isinstance(method, str):
        if message_id is None:
            return True, None
        return True, jsonrpc_error(message_id, -32600, "invalid request: method missing")

    if method == "initialize":
        response = {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {
                "tools": {},
            },
            "serverInfo": SERVER_INFO,
        }
        if message_id is None:
            return True, None
        return True, jsonrpc_success(message_id, response)

    if method == "ping":
        if message_id is None:
            return True, None
        return True, jsonrpc_success(message_id, {})

    if method == "tools/list":
        if message_id is None:
            return True, None
        return True, jsonrpc_success(message_id, {"tools": TOOL_DEFS})

    if method == "tools/call":
        if message_id is None:
            return True, None
        return True, jsonrpc_success(message_id, _handle_tools_call(params))

    if method == "notifications/initialized":
        return True, None

    if method == "shutdown":
        if message_id is None:
            return False, None
        return False, jsonrpc_success(message_id, {})

    if message_id is None:
        return True, None

    return True, jsonrpc_error(message_id, -32601, f"method not found: {method}")


def run_server() -> int:
    stdin = sys.stdin.buffer
    stdout = sys.stdout.buffer

    while True:
        try:
            message = read_message(stdin)
        except ProtocolError as exc:
            # Invalid framing: cannot safely recover message id.
            print(f"protocol error: {exc}", file=sys.stderr)
            return 1

        if message is None:
            return 0

        should_continue, response = _handle_request(message)
        if response is not None:
            write_message(stdout, response)

        if not should_continue:
            return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run control-room MCP scaffold server")
    parser.parse_args()
    return run_server()


if __name__ == "__main__":
    raise SystemExit(main())
