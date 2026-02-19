#!/usr/bin/env python3
"""Minimal JSON-RPC-over-stdio framing helpers (MCP-compatible transport)."""

from __future__ import annotations

import json
from typing import Any, BinaryIO, Dict, Optional


class ProtocolError(Exception):
    """Raised for malformed JSON-RPC framing."""


_HEADER_CONTENT_LENGTH = "content-length"


def read_message(stream: BinaryIO) -> Optional[Dict[str, Any]]:
    """Read one framed JSON-RPC message from a binary stream.

    Returns None when EOF is reached before any header bytes are read.
    """
    headers: Dict[str, str] = {}

    while True:
        line = stream.readline()
        if line == b"":
            if not headers:
                return None
            raise ProtocolError("unexpected EOF while reading headers")

        stripped = line.strip()
        if stripped == b"":
            break

        if b":" not in line:
            raise ProtocolError("malformed header line")

        key_raw, value_raw = line.split(b":", 1)
        key = key_raw.decode("ascii", errors="strict").strip().lower()
        value = value_raw.decode("ascii", errors="strict").strip()
        headers[key] = value

    if _HEADER_CONTENT_LENGTH not in headers:
        raise ProtocolError("missing Content-Length header")

    try:
        content_length = int(headers[_HEADER_CONTENT_LENGTH])
    except ValueError as exc:
        raise ProtocolError("invalid Content-Length header") from exc

    if content_length < 0:
        raise ProtocolError("negative Content-Length header")

    payload = stream.read(content_length)
    if len(payload) != content_length:
        raise ProtocolError("unexpected EOF while reading payload")

    try:
        decoded = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProtocolError("invalid JSON payload") from exc

    if not isinstance(decoded, dict):
        raise ProtocolError("top-level JSON-RPC payload must be an object")

    return decoded


def write_message(stream: BinaryIO, payload: Dict[str, Any]) -> None:
    """Write one framed JSON-RPC message to a binary stream."""
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    header = f"Content-Length: {len(raw)}\r\n\r\n".encode("ascii")
    stream.write(header)
    stream.write(raw)
    stream.flush()


def jsonrpc_success(message_id: Any, result: Dict[str, Any]) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": message_id, "result": result}


def jsonrpc_error(message_id: Any, code: int, message: str) -> Dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": message_id,
        "error": {
            "code": code,
            "message": message,
        },
    }
