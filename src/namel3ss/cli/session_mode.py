from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
import urllib.request

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message


DEFAULT_SERVICE_HOST = "127.0.0.1"
DEFAULT_SERVICE_PORT = 8787



def run_session_command(args: list[str]) -> int:
    if not args:
        raise Namel3ssError(
            build_guidance_message(
                what="Missing session subcommand.",
                why="Session commands require list or kill.",
                fix="Use list or kill <session_id>.",
                example="n3 session list",
            )
        )
    command = str(args[0]).strip().lower()
    if command == "list":
        host, port = _parse_host_port(args[1:])
        payload = _request_json("GET", _service_url(host, port, "/api/service/sessions"))
        sessions = payload.get("sessions") if isinstance(payload, dict) else None
        print("active sessions:")
        if not isinstance(sessions, list) or not sessions:
            print("- none")
            return 0
        for item in sessions:
            if not isinstance(item, dict):
                continue
            session_id = str(item.get("session_id") or "")
            role = str(item.get("role") or "")
            last_activity = str(item.get("last_activity") or "")
            print(f"- {session_id} role={role} last_activity={last_activity}")
        return 0
    if command == "kill":
        if len(args) < 2:
            raise Namel3ssError(
                build_guidance_message(
                    what="Missing session id.",
                    why="Session kill requires a session id.",
                    fix="Pass the session id after kill.",
                    example="n3 session kill s000001",
                )
            )
        session_id = str(args[1]).strip()
        host, port = _parse_host_port(args[2:])
        payload = _request_json("DELETE", _service_url(host, port, f"/api/service/sessions/{session_id}"))
        if not bool(payload.get("ok")):
            raise Namel3ssError(str(payload.get("error") or "Failed to terminate session."))
        print(f"terminated session: {session_id}")
        return 0
    raise Namel3ssError(
        build_guidance_message(
            what=f"Unknown session subcommand '{command}'.",
            why="Session commands support list and kill.",
            fix="Use n3 session list or n3 session kill <session_id>.",
            example="n3 session list",
        )
    )



def _parse_host_port(args: list[str]) -> tuple[str, int]:
    host = DEFAULT_SERVICE_HOST
    port = DEFAULT_SERVICE_PORT
    i = 0
    while i < len(args):
        token = args[i]
        if token == "--host":
            if i + 1 >= len(args):
                raise Namel3ssError("--host requires a value")
            host = str(args[i + 1]).strip() or DEFAULT_SERVICE_HOST
            i += 2
            continue
        if token == "--port":
            if i + 1 >= len(args):
                raise Namel3ssError("--port requires a value")
            try:
                port = int(args[i + 1])
            except ValueError as err:
                raise Namel3ssError("--port must be an integer") from err
            i += 2
            continue
        raise Namel3ssError(f"Unknown flag '{token}'. Supported flags: --host, --port.")
    return host, port



def _service_url(host: str, port: int, path: str) -> str:
    return f"http://{host}:{int(port)}{path}"



def _request_json(method: str, url: str) -> dict:
    req = urllib.request.Request(url=url, method=method)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req) as response:  # noqa: S310
            raw = response.read().decode("utf-8")
    except HTTPError as err:
        details = err.read().decode("utf-8", errors="replace")
        raise Namel3ssError(f"Service request failed ({err.code}): {details or err.reason}") from err
    except URLError as err:
        raise Namel3ssError(f"Could not reach service: {err.reason}") from err
    try:
        payload = json.loads(raw or "{}")
    except json.JSONDecodeError as err:
        raise Namel3ssError("Service returned invalid JSON.") from err
    if isinstance(payload, dict):
        return payload
    raise Namel3ssError("Service returned an invalid payload.")


__all__ = ["run_session_command"]
