#!/usr/bin/env python3
"""Skill-Lab MCP scaffold server.

Scaffold-only implementation for discover/learn/level transitions.
Persists lightweight state to JSON so flows can be prototyped end-to-end.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any, Dict, Tuple

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.mcp.jsonrpc_stdio import (  # type: ignore
    ProtocolError,
    jsonrpc_error,
    jsonrpc_success,
    read_message,
    write_message,
)

PROTOCOL_VERSION = "2025-03-26"
SERVER_INFO = {"name": "skill-lab-mcp", "version": "0.1.0-scaffold"}

DEFAULT_STATE_PATH = ROOT / "status/skill-lab/scaffold-state.json"

TOOL_DEFS = [
    {
        "name": "skill-lab.state.get",
        "description": "Return current Skill-Lab scaffold state.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "stateFile": {"type": "string"},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "skill-lab.discover",
        "description": "Create a candidate locked skill linked to a source skill.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "stateFile": {"type": "string"},
                "name": {"type": "string"},
                "fromSkillId": {"type": "string"},
                "rationale": {"type": "string"},
            },
            "required": ["name", "fromSkillId"],
            "additionalProperties": False,
        },
    },
    {
        "name": "skill-lab.learn.start",
        "description": "Start a scaffold learning job for a skill.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "stateFile": {"type": "string"},
                "skillId": {"type": "string"},
            },
            "required": ["skillId"],
            "additionalProperties": False,
        },
    },
    {
        "name": "skill-lab.level.transition",
        "description": "Apply deterministic level/tier transition to a skill.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "stateFile": {"type": "string"},
                "skillId": {"type": "string"},
                "tier": {"type": "integer", "minimum": 0, "maximum": 5},
                "level": {"type": "integer", "minimum": 0, "maximum": 100},
                "progress": {"type": "integer", "minimum": 0, "maximum": 100},
            },
            "required": ["skillId"],
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


def _resolve_state_file(raw: Any) -> Path:
    if isinstance(raw, str) and raw.strip():
        path = Path(raw)
        if path.is_absolute():
            return path
        return (ROOT / path).resolve()
    return DEFAULT_STATE_PATH


def _empty_state() -> Dict[str, Any]:
    now = dt.datetime.now().astimezone().isoformat()
    return {
        "version": "0.1.0-scaffold",
        "updatedAt": now,
        "skills": {},
        "jobs": {},
    }


def _load_state(state_file: Path) -> Dict[str, Any]:
    if not state_file.exists():
        return _empty_state()

    try:
        raw = json.loads(state_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return _empty_state()

    if not isinstance(raw, dict):
        return _empty_state()

    if not isinstance(raw.get("skills"), dict):
        raw["skills"] = {}
    if not isinstance(raw.get("jobs"), dict):
        raw["jobs"] = {}

    return raw


def _save_state(state_file: Path, state: Dict[str, Any]) -> None:
    state["updatedAt"] = dt.datetime.now().astimezone().isoformat()
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def _ensure_skill(state: Dict[str, Any], skill_id: str) -> Dict[str, Any]:
    skills = state["skills"]
    current = skills.get(skill_id)
    if isinstance(current, dict):
        return current

    seeded = {
        "id": skill_id,
        "name": skill_id,
        "state": "locked",
        "tier": 0,
        "level": 0,
        "progress": 0,
        "dependencies": [],
        "lastTransitionAt": "",
    }
    skills[skill_id] = seeded
    return seeded


def tool_state_get(arguments: Dict[str, Any]) -> Dict[str, Any]:
    state_file = _resolve_state_file(arguments.get("stateFile"))
    state = _load_state(state_file)
    return {
        "stateFile": str(state_file),
        "state": state,
    }


def tool_discover(arguments: Dict[str, Any]) -> Dict[str, Any]:
    state_file = _resolve_state_file(arguments.get("stateFile"))
    name = str(arguments.get("name") or "").strip()
    from_skill_id = str(arguments.get("fromSkillId") or "").strip()
    rationale = str(arguments.get("rationale") or "").strip()

    if not name:
        raise ValueError("name is required")
    if not from_skill_id:
        raise ValueError("fromSkillId is required")

    state = _load_state(state_file)
    parent = _ensure_skill(state, from_skill_id)

    candidate_id = f"candidate-{name.lower().replace(' ', '-')[:40]}"
    candidate = _ensure_skill(state, candidate_id)
    candidate.update(
        {
            "name": name,
            "state": "locked",
            "tier": 0,
            "progress": 0,
            "dependencies": [parent["id"]],
            "discoveredFrom": parent["id"],
            "rationale": rationale,
            "lastTransitionAt": dt.datetime.now().astimezone().isoformat(),
        }
    )

    _save_state(state_file, state)
    return {
        "stateFile": str(state_file),
        "skill": candidate,
    }


def tool_learn_start(arguments: Dict[str, Any]) -> Dict[str, Any]:
    state_file = _resolve_state_file(arguments.get("stateFile"))
    skill_id = str(arguments.get("skillId") or "").strip()
    if not skill_id:
        raise ValueError("skillId is required")

    state = _load_state(state_file)
    skill = _ensure_skill(state, skill_id)
    now_iso = dt.datetime.now().astimezone().isoformat()

    skill["state"] = "in-progress"
    skill["lastTransitionAt"] = now_iso

    job_id = f"learn-{skill_id}-{int(dt.datetime.now().timestamp())}"
    state["jobs"][job_id] = {
        "jobId": job_id,
        "skillId": skill_id,
        "state": "running",
        "startedAt": now_iso,
    }

    _save_state(state_file, state)
    return {
        "stateFile": str(state_file),
        "job": state["jobs"][job_id],
        "skill": skill,
    }


def tool_level_transition(arguments: Dict[str, Any]) -> Dict[str, Any]:
    state_file = _resolve_state_file(arguments.get("stateFile"))
    skill_id = str(arguments.get("skillId") or "").strip()
    if not skill_id:
        raise ValueError("skillId is required")

    state = _load_state(state_file)
    skill = _ensure_skill(state, skill_id)

    tier = arguments.get("tier")
    level = arguments.get("level")
    progress = arguments.get("progress")

    if isinstance(tier, int):
        skill["tier"] = max(0, min(5, tier))
    else:
        skill["tier"] = min(5, int(skill.get("tier", 0)) + 1)

    if isinstance(level, int):
        skill["level"] = max(0, min(100, level))
    else:
        skill["level"] = max(skill.get("level", 0), skill["tier"] * 20)

    if isinstance(progress, int):
        skill["progress"] = max(0, min(100, progress))
    else:
        skill["progress"] = 0 if skill["tier"] >= 5 else 25

    skill["state"] = "active" if skill["tier"] > 0 else skill.get("state", "locked")
    skill["lastTransitionAt"] = dt.datetime.now().astimezone().isoformat()

    _save_state(state_file, state)
    return {
        "stateFile": str(state_file),
        "skill": skill,
    }


TOOL_HANDLERS = {
    "skill-lab.state.get": tool_state_get,
    "skill-lab.discover": tool_discover,
    "skill-lab.learn.start": tool_learn_start,
    "skill-lab.level.transition": tool_level_transition,
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
    except Exception as exc:  # pragma: no cover - ad-hoc scaffold safety net
        return _tool_result(
            text=f"tool failed: {exc}",
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
        result = {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {}},
            "serverInfo": SERVER_INFO,
        }
        if message_id is None:
            return True, None
        return True, jsonrpc_success(message_id, result)

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
    parser = argparse.ArgumentParser(description="Run skill-lab MCP scaffold server")
    parser.parse_args()
    return run_server()


if __name__ == "__main__":
    raise SystemExit(main())
