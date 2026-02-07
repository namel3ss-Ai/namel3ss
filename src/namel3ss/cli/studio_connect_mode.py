from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
import urllib.request

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message


DEFAULT_SERVICE_HOST = "127.0.0.1"
DEFAULT_SERVICE_PORT = 8787



def run_studio_connect_command(args: list[str]) -> int:
    if not args:
        raise Namel3ssError(
            build_guidance_message(
                what="Missing session id.",
                why="Studio connect needs a target service session id.",
                fix="Pass a session id after connect.",
                example="n3 studio connect s000001 --host 127.0.0.1 --port 8787",
            )
        )
    session_id = str(args[0]).strip()
    if not session_id:
        raise Namel3ssError("Session id cannot be empty.")
    host, port, json_mode = _parse_args(args[1:])
    state_payload = _request_json("GET", _service_url(host, port, f"/api/service/studio/{session_id}/state"))
    traces_payload = _request_json("GET", _service_url(host, port, f"/api/service/studio/{session_id}/traces"))
    payload = {
        "ok": True,
        "host": host,
        "port": port,
        "session_id": session_id,
        "state": state_payload.get("state"),
        "traces": traces_payload.get("traces"),
    }
    if json_mode:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    print(f"Studio remote session: {session_id}")
    print(f"Service host: http://{host}:{port}")
    print(f"State keys: {', '.join(sorted((payload.get('state') or {}).keys())) if isinstance(payload.get('state'), dict) else 'none'}")
    trace_count = len(payload.get("traces") or []) if isinstance(payload.get("traces"), list) else 0
    print(f"Trace events: {trace_count}")
    return 0



def _parse_args(args: list[str]) -> tuple[str, int, bool]:
    host = DEFAULT_SERVICE_HOST
    port = DEFAULT_SERVICE_PORT
    json_mode = False
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
        if token == "--json":
            json_mode = True
            i += 1
            continue
        raise Namel3ssError(f"Unknown flag '{token}'. Supported flags: --host, --port, --json.")
    return host, port, json_mode



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
        raise Namel3ssError(f"Studio connection failed ({err.code}): {details or err.reason}") from err
    except URLError as err:
        raise Namel3ssError(f"Could not reach service: {err.reason}") from err
    try:
        payload = json.loads(raw or "{}")
    except json.JSONDecodeError as err:
        raise Namel3ssError("Service returned invalid JSON.") from err
    if not isinstance(payload, dict):
        raise Namel3ssError("Service returned an invalid payload.")
    if payload.get("ok") is False:
        raise Namel3ssError(str(payload.get("error") or "Request failed."))
    return payload


__all__ = ["run_studio_connect_command"]
