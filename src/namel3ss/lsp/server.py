from __future__ import annotations

import json
import re
from typing import BinaryIO

from namel3ss.errors.base import Namel3ssError
from namel3ss.lang.keywords import KEYWORD_LIST
from namel3ss.parser.core import Parser


class LspState:
    def __init__(self) -> None:
        self.documents: dict[str, str] = {}
        self.shutting_down = False


def serve_stdio(reader: BinaryIO, writer: BinaryIO) -> None:
    state = LspState()
    while True:
        message = _read_message(reader)
        if message is None:
            break
        response, notifications = _handle_message(state, message)
        if response is not None:
            _write_message(writer, response)
        for note in notifications:
            _write_message(writer, note)
        if state.shutting_down:
            break


def diagnostics_for_text(source: str) -> list[dict[str, object]]:
    try:
        Parser.parse(source)
        return []
    except Namel3ssError as err:
        line = max(0, int(err.line or 1) - 1)
        col = max(0, int(err.column or 1) - 1)
        end_col = col + 1
        return [
            {
                "range": {
                    "start": {"line": line, "character": col},
                    "end": {"line": line, "character": end_col},
                },
                "severity": 1,
                "message": err.message,
                "source": "namel3ss",
            }
        ]
    except Exception as err:  # pragma: no cover - defensive fallback
        return [
            {
                "range": {
                    "start": {"line": 0, "character": 0},
                    "end": {"line": 0, "character": 1},
                },
                "severity": 1,
                "message": str(err),
                "source": "namel3ss",
            }
        ]


def _handle_message(state: LspState, message: dict) -> tuple[dict | None, list[dict]]:
    method = str(message.get("method") or "")
    msg_id = message.get("id")
    params = message.get("params") if isinstance(message.get("params"), dict) else {}
    notifications: list[dict] = []

    if method == "initialize":
        return (
            {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "capabilities": {
                        "textDocumentSync": 1,
                        "completionProvider": {"resolveProvider": False},
                        "definitionProvider": True,
                        "renameProvider": True,
                    },
                    "serverInfo": {"name": "namel3ss-lsp", "version": "0.1"},
                },
            },
            notifications,
        )

    if method == "shutdown":
        state.shutting_down = True
        return {"jsonrpc": "2.0", "id": msg_id, "result": None}, notifications

    if method == "exit":
        state.shutting_down = True
        return None, notifications

    if method == "textDocument/didOpen":
        text_doc = params.get("textDocument") if isinstance(params, dict) else None
        if isinstance(text_doc, dict):
            uri = str(text_doc.get("uri") or "")
            text = str(text_doc.get("text") or "")
            state.documents[uri] = text
            notifications.append(_publish_diagnostics(uri, text))
        return None, notifications

    if method == "textDocument/didChange":
        text_doc = params.get("textDocument") if isinstance(params, dict) else None
        changes = params.get("contentChanges") if isinstance(params, dict) else None
        if isinstance(text_doc, dict) and isinstance(changes, list) and changes:
            uri = str(text_doc.get("uri") or "")
            latest = changes[-1]
            if isinstance(latest, dict):
                text = str(latest.get("text") or "")
                state.documents[uri] = text
                notifications.append(_publish_diagnostics(uri, text))
        return None, notifications

    if method == "textDocument/completion":
        result = {
            "isIncomplete": False,
            "items": [
                {
                    "label": keyword,
                    "kind": 14,
                    "detail": "keyword",
                }
                for keyword in KEYWORD_LIST
            ],
        }
        return {"jsonrpc": "2.0", "id": msg_id, "result": result}, notifications

    if method == "textDocument/definition":
        uri = _uri_from_params(params)
        source = state.documents.get(uri, "")
        position = params.get("position") if isinstance(params, dict) else {}
        word = _word_at_position(source, position)
        location = _definition_location(uri, source, word)
        return {"jsonrpc": "2.0", "id": msg_id, "result": location}, notifications

    if method == "textDocument/rename":
        uri = _uri_from_params(params)
        source = state.documents.get(uri, "")
        position = params.get("position") if isinstance(params, dict) else {}
        new_name = str(params.get("newName") or "")
        old_name = _word_at_position(source, position)
        edits = _rename_edits(source, old_name, new_name)
        result = {"changes": {uri: edits}} if uri else {"changes": {}}
        return {"jsonrpc": "2.0", "id": msg_id, "result": result}, notifications

    if method == "namel3ss/diagnostics":
        uri = _uri_from_params(params)
        source = state.documents.get(uri, "")
        if not source:
            source = str(params.get("text") or "")
        return {"jsonrpc": "2.0", "id": msg_id, "result": diagnostics_for_text(source)}, notifications

    if msg_id is not None:
        return {"jsonrpc": "2.0", "id": msg_id, "result": None}, notifications
    return None, notifications


def _publish_diagnostics(uri: str, source: str) -> dict[str, object]:
    return {
        "jsonrpc": "2.0",
        "method": "textDocument/publishDiagnostics",
        "params": {
            "uri": uri,
            "diagnostics": diagnostics_for_text(source),
        },
    }


def _uri_from_params(params: dict) -> str:
    text_doc = params.get("textDocument") if isinstance(params, dict) else None
    if isinstance(text_doc, dict):
        return str(text_doc.get("uri") or "")
    return ""


def _word_at_position(source: str, position: object) -> str:
    if not isinstance(position, dict):
        return ""
    line_index = int(position.get("line") or 0)
    char_index = int(position.get("character") or 0)
    lines = source.splitlines()
    if line_index < 0 or line_index >= len(lines):
        return ""
    line = lines[line_index]
    if not line:
        return ""
    char_index = max(0, min(char_index, len(line) - 1))

    start = char_index
    while start > 0 and _is_word_char(line[start - 1]):
        start -= 1
    end = char_index
    while end < len(line) and _is_word_char(line[end]):
        end += 1
    return line[start:end]


def _definition_location(uri: str, source: str, word: str) -> list[dict[str, object]]:
    if not uri or not source or not word:
        return []
    pattern = re.compile(rf'^(flow|record|qa|translate|cot|chain|classification|summarise|rag)\s+"{re.escape(word)}"', re.MULTILINE)
    match = pattern.search(source)
    if not match:
        return []
    start_offset = match.start()
    line = source.count("\n", 0, start_offset)
    col = start_offset - (source.rfind("\n", 0, start_offset) + 1 if "\n" in source[:start_offset] else 0)
    return [
        {
            "uri": uri,
            "range": {
                "start": {"line": line, "character": col},
                "end": {"line": line, "character": col + len(word)},
            },
        }
    ]


def _rename_edits(source: str, old_name: str, new_name: str) -> list[dict[str, object]]:
    if not old_name or not new_name or old_name == new_name:
        return []
    edits: list[dict[str, object]] = []
    lines = source.splitlines()
    for line_index, line in enumerate(lines):
        for match in re.finditer(rf"\b{re.escape(old_name)}\b", line):
            edits.append(
                {
                    "range": {
                        "start": {"line": line_index, "character": match.start()},
                        "end": {"line": line_index, "character": match.end()},
                    },
                    "newText": new_name,
                }
            )
    return edits


def _is_word_char(char: str) -> bool:
    return char.isalnum() or char in {"_", ".", '"'}


def _read_message(reader: BinaryIO) -> dict | None:
    headers: dict[str, str] = {}
    while True:
        line = reader.readline()
        if not line:
            return None
        if line in {b"\r\n", b"\n"}:
            break
        text = line.decode("utf-8", errors="replace").strip()
        if ":" not in text:
            continue
        key, value = text.split(":", 1)
        headers[key.strip().lower()] = value.strip()

    length_raw = headers.get("content-length")
    if length_raw is None:
        return None
    length = int(length_raw)
    body = reader.read(length)
    if not body:
        return None
    try:
        payload = json.loads(body.decode("utf-8"))
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _write_message(writer: BinaryIO, payload: dict) -> None:
    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    header = f"Content-Length: {len(body)}\r\n\r\n".encode("ascii")
    writer.write(header)
    writer.write(body)
    writer.flush()


__all__ = ["diagnostics_for_text", "serve_stdio"]
