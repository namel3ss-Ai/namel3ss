from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Dict

from namel3ss.editor.diagnostics import diagnose
from namel3ss.editor.fixes import fix_for_diagnostic
from namel3ss.editor.index import build_index
from namel3ss.editor.navigation import get_definition, get_hover
from namel3ss.editor.rename import rename_symbol
from namel3ss.editor.workspace import EditorWorkspace, normalize_path
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message


DEFAULT_EDITOR_PORT = 7333


class EditorRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:  # pragma: no cover - silence logs
        pass

    def do_GET(self) -> None:  # noqa: N802
        if self.path.startswith("/health"):
            self._respond_json({"status": "ok"})
            return
        self.send_error(404)

    def do_POST(self) -> None:  # noqa: N802
        try:
            payload = self._read_json()
        except ValueError as err:
            self._respond_error(
                Namel3ssError(
                    build_guidance_message(
                        what="Invalid JSON payload.",
                        why=str(err),
                        fix="Send valid JSON with the request.",
                        example='{"file":"app.ai"}',
                    )
                )
            )
            return

        try:
            if self.path == "/diagnose":
                self._handle_diagnose(payload)
                return
            if self.path == "/symbols":
                self._handle_symbols(payload)
                return
            if self.path == "/definition":
                self._handle_definition(payload)
                return
            if self.path == "/hover":
                self._handle_hover(payload)
                return
            if self.path == "/rename":
                self._handle_rename(payload)
                return
            if self.path == "/fix":
                self._handle_fix(payload)
                return
        except Namel3ssError as err:
            self._respond_error(err)
            return

        self.send_error(404)

    def _handle_diagnose(self, payload: dict) -> None:
        workspace = self._workspace_from_payload(payload)
        overrides = workspace.build_overrides(payload.get("files"))
        diagnostics = diagnose(workspace, overrides=overrides)
        self._respond_json({"diagnostics": [diag.to_dict() for diag in diagnostics]})

    def _handle_symbols(self, payload: dict) -> None:
        workspace = self._workspace_from_payload(payload)
        overrides = workspace.build_overrides(payload.get("files"))
        project = workspace.load(overrides)
        index = build_index(project)
        symbols = []
        for definition in index.definitions.values():
            symbols.append(
                {
                    "kind": definition.kind,
                    "name": definition.name,
                    "file": normalize_path(definition.file, index.root),
                    "line": definition.span.line,
                    "column": definition.span.column,
                    "capsule": definition.module or (definition.name if definition.kind == "capsule" else None),
                    "origin": definition.origin,
                    "exported": bool(definition.exported),
                }
            )
        symbols = sorted(symbols, key=lambda s: (s["kind"], s["name"], s["file"]))
        self._respond_json({"symbols": symbols})

    def _handle_definition(self, payload: dict) -> None:
        file_path, line, column = self._parse_position(payload)
        workspace = self._workspace_from_payload(payload)
        overrides = workspace.build_overrides(payload.get("files"))
        project = workspace.load(overrides)
        index = build_index(project)
        location = get_definition(index, file_path=file_path, line=line, column=column)
        if location is None:
            self._respond_json({"found": False})
            return
        self._respond_json({"found": True, "definition": location.to_dict()})

    def _handle_hover(self, payload: dict) -> None:
        file_path, line, column = self._parse_position(payload)
        workspace = self._workspace_from_payload(payload)
        overrides = workspace.build_overrides(payload.get("files"))
        project = workspace.load(overrides)
        index = build_index(project)
        contents = get_hover(index, file_path=file_path, line=line, column=column)
        if contents is None:
            self._respond_json({"found": False})
            return
        self._respond_json({"found": True, "contents": contents})

    def _handle_rename(self, payload: dict) -> None:
        file_path, line, column = self._parse_position(payload)
        new_name = str(payload.get("new_name") or "")
        workspace = self._workspace_from_payload(payload)
        overrides = workspace.build_overrides(payload.get("files"))
        project = workspace.load(overrides)
        index = build_index(project)
        edits = rename_symbol(index, file_path=file_path, line=line, column=column, new_name=new_name)
        self._respond_json({"status": "ok", "edits": [edit.to_dict() for edit in edits]})

    def _handle_fix(self, payload: dict) -> None:
        file_path = self._parse_file(payload)
        diagnostic_id = str(payload.get("diagnostic_id") or "")
        workspace = self._workspace_from_payload(payload)
        overrides = workspace.build_overrides(payload.get("files"))
        source = overrides.get(file_path)
        if source is None:
            source = file_path.read_text(encoding="utf-8")
        edits = fix_for_diagnostic(
            root=workspace.root,
            file_path=file_path,
            diagnostic_id=diagnostic_id,
            source=source,
        )
        self._respond_json({"status": "ok", "edits": [edit.to_dict() for edit in edits]})

    def _workspace_from_payload(self, payload: dict) -> EditorWorkspace:
        entry = payload.get("entry")
        workspace = self.server.workspace  # type: ignore[attr-defined]
        if entry:
            entry_path = Path(str(entry))
            if not entry_path.is_absolute():
                entry_path = workspace.root / entry_path
            return EditorWorkspace.from_app_path(entry_path)
        return workspace

    def _parse_file(self, payload: dict) -> Path:
        raw = payload.get("file")
        if not raw:
            raise Namel3ssError(
                build_guidance_message(
                    what="Missing file path in request.",
                    why="Editor requests require a file path.",
                    fix="Provide the file field.",
                    example='{"file":"app.ai"}',
                )
            )
        path = Path(str(raw))
        workspace = self.server.workspace  # type: ignore[attr-defined]
        if not path.is_absolute():
            path = workspace.root / path
        return _safe_resolve(path)

    def _parse_position(self, payload: dict) -> tuple[Path, int, int]:
        file_path = self._parse_file(payload)
        pos = payload.get("position") or {}
        line = int(pos.get("line", 0))
        column = int(pos.get("column", 0))
        if line <= 0 or column <= 0:
            raise Namel3ssError(
                build_guidance_message(
                    what="Position is missing or invalid.",
                    why="Editor requests need 1-based line and column.",
                    fix="Provide position.line and position.column.",
                    example='{"position":{"line":1,"column":1}}',
                )
            )
        return file_path, line, column

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b""
        if not raw:
            return {}
        return json.loads(raw.decode("utf-8"))

    def _respond_error(self, err: Namel3ssError) -> None:
        what, why, fix, example = _parse_guidance(err.message)
        payload = {
            "status": "error",
            "what": what or err.message,
            "why": why or "The editor could not complete the request.",
            "fix": fix or "Review the request and retry.",
            "example": example or "n3 editor",
        }
        self._respond_json(payload, status=400)

    def _respond_json(self, payload: dict, status: int = 200) -> None:
        data = json.dumps(payload, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


class EditorServer:
    def __init__(self, app_path: Path, *, port: int | None = None, host: str = "127.0.0.1") -> None:
        self.workspace = EditorWorkspace.from_app_path(app_path)
        self.port = DEFAULT_EDITOR_PORT if port is None else port
        self.host = host
        self.server: HTTPServer | None = None
        self._thread: threading.Thread | None = None

    def start(self, *, background: bool = False) -> None:
        self.bind()
        server = self.server
        if server is None:
            return
        if background:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            self._thread = thread
        else:
            server.serve_forever()

    def shutdown(self) -> None:
        if self.server:
            try:
                self.server.shutdown()
            except Exception:
                pass
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1)

    @property
    def bound_port(self) -> int:
        if self.server:
            return int(self.server.server_address[1])
        return self.port

    def bind(self) -> None:
        if self.server is None:
            self.server = self._bind_server()

    def _bind_server(self) -> HTTPServer:
        if self.port != DEFAULT_EDITOR_PORT:
            return self._create_server(self.port)
        for offset in range(20):
            try:
                return self._create_server(DEFAULT_EDITOR_PORT + offset)
            except OSError:
                continue
        raise Namel3ssError(
            build_guidance_message(
                what="No available editor port found.",
                why="Ports 7333-7352 are in use.",
                fix="Pick a free port with --port.",
                example="n3 editor --port 7444",
            )
        )

    def _create_server(self, port: int) -> HTTPServer:
        server = HTTPServer((self.host, port), EditorRequestHandler)
        server.workspace = self.workspace  # type: ignore[attr-defined]
        return server


def _parse_guidance(message: str) -> tuple[str, str, str, str]:
    what = ""
    why = ""
    fix = ""
    example = ""
    for line in message.splitlines():
        if line.startswith("What happened:"):
            what = line.split("What happened:", 1)[1].strip()
        elif line.startswith("Why:"):
            why = line.split("Why:", 1)[1].strip()
        elif line.startswith("Fix:"):
            fix = line.split("Fix:", 1)[1].strip()
        elif line.startswith("Example:"):
            example = line.split("Example:", 1)[1].strip()
    return what, why, fix, example


def _safe_resolve(path: Path) -> Path:
    try:
        return path.resolve()
    except FileNotFoundError:
        return path.absolute()


__all__ = ["EditorServer", "DEFAULT_EDITOR_PORT"]
