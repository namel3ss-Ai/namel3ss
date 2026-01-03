from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.secrets import collect_secret_values, redact_text
from namel3ss.utils.json_tools import dumps as json_dumps


PROTOCOL_VERSION = 1

_RUNNER = r"""
import json
import sys
import importlib
import io
import contextlib
from decimal import Decimal

try:
    import namel3ss_safeio as _safeio
except Exception:
    _safeio = None

try:
    from namel3ss.runtime.tools.python_sandbox import bootstrap as _sandbox
except Exception:
    _sandbox = None


def _json_default(value):
    if isinstance(value, Decimal):
        if value == value.to_integral_value():
            return int(value)
        text = format(value.normalize(), "f")
        return text
    raise TypeError(f"Object of type {type(value)} is not JSON serializable")


def _error_payload(err, protocol_version, checks):
    error = {"type": err.__class__.__name__, "message": str(err)}
    reason = getattr(getattr(err, "check", None), "reason", None)
    if isinstance(reason, str):
        error["reason_code"] = reason
    return {
        "ok": False,
        "error": error,
        "protocol_version": protocol_version,
        "capability_checks": checks,
    }


def _run_plain(payload):
    entry = payload.get("entry")
    args = payload.get("payload")
    protocol_version = payload.get("protocol_version", 1)
    if not isinstance(entry, str):
        return _error_payload(ValueError("Missing entry"), protocol_version, [])
    try:
        module_path, function_name = entry.split(":", 1)
    except ValueError:
        return _error_payload(ValueError("Invalid entry"), protocol_version, [])
    try:
        context = payload.get("capability_context")
        sandbox_active = False
        module = importlib.import_module(module_path)
        func = getattr(module, function_name)
        if not callable(func):
            raise TypeError("Entry target is not callable")
        if _sandbox is not None and isinstance(context, dict):
            _sandbox.configure(context)
            sandbox_active = True
        elif _safeio is not None and isinstance(context, dict):
            _safeio.configure(context)
        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()
        with contextlib.redirect_stdout(stdout_buf), contextlib.redirect_stderr(stderr_buf):
            result = func(args)
        checks = []
        if sandbox_active:
            checks = _sandbox.drain_checks()
        elif _safeio is not None:
            checks = _safeio.drain_checks()
        return {
            "ok": True,
            "result": result,
            "protocol_version": protocol_version,
            "capability_checks": checks,
        }
    except Exception as err:
        checks = []
        if sandbox_active:
            checks = _sandbox.drain_checks()
        elif _safeio is not None:
            checks = _safeio.drain_checks()
        return _error_payload(err, protocol_version, checks)


def _run_payload(payload):
    protocol_version = payload.get("protocol_version", 1)
    if payload.get("sandbox"):
        if _sandbox is None:
            return _error_payload(RuntimeError("Sandbox bootstrap unavailable"), protocol_version, [])
        return _sandbox.run(payload)
    return _run_plain(payload)


def _main():
    try:
        payload = json.load(sys.stdin)
    except Exception as err:
        sys.stdout.write(
            json.dumps(
                {"ok": False, "error": {"type": err.__class__.__name__, "message": str(err)}, "protocol_version": 1}
            )
        )
        return 1
    output = _run_payload(payload)
    if not isinstance(output, dict) or "ok" not in output:
        output = {
            "ok": False,
            "error": {"type": "ValueError", "message": "Invalid tool response"},
            "protocol_version": payload.get("protocol_version", 1),
        }
    try:
        sys.stdout.write(json.dumps(output, default=_json_default))
        return 0
    except Exception as err:
        fallback = {
            "ok": False,
            "error": {"type": err.__class__.__name__, "message": str(err)},
            "protocol_version": payload.get("protocol_version", 1),
        }
        sys.stdout.write(json.dumps(fallback))
        return 1


if __name__ == "__main__":
    raise SystemExit(_main())
"""


@dataclass(frozen=True)
class ToolSubprocessResult:
    ok: bool
    output: object | None
    error_type: str | None
    error_message: str | None
    capability_checks: list[dict[str, object]] | None = None


def run_tool_subprocess(
    *,
    python_path: Path,
    tool_name: str,
    entry: str,
    payload: dict,
    app_root: Path,
    timeout_seconds: int,
    extra_paths: list[Path] | None = None,
    capability_context: dict[str, object] | None = None,
    sandbox: bool = False,
    trace_id: str | None = None,
) -> ToolSubprocessResult:
    request = {
        "protocol_version": PROTOCOL_VERSION,
        "tool": tool_name,
        "entry": entry,
        "payload": payload,
    }
    if capability_context:
        request["capability_context"] = capability_context
    if sandbox:
        request["sandbox"] = True
    if trace_id:
        request["trace_id"] = trace_id
    input_text = json_dumps(request)
    env = _build_env(app_root, extra_paths=extra_paths)
    try:
        result = subprocess.run(
            [str(python_path), "-c", _RUNNER],
            input=input_text,
            text=True,
            capture_output=True,
            env=env,
            cwd=str(app_root),
            timeout=timeout_seconds,
            check=False,
        )
    except FileNotFoundError as err:
        raise Namel3ssError(
            build_guidance_message(
                what="Python interpreter was not found.",
                why=str(err),
                fix="Recreate the venv or check the python path.",
                example="n3 deps install --force",
            )
        ) from err
    except subprocess.TimeoutExpired as err:
        raise Namel3ssError(
            build_guidance_message(
                what="Python tool execution timed out.",
                why=f"Tool exceeded {timeout_seconds}s timeout.",
                fix="Increase timeout_seconds or optimize the tool.",
                example=(
                    "tool \"calc\":\n"
                    "  implemented using python\n"
                    "  timeout_seconds is 20\n\n"
                    "  input:\n"
                    "    value is number\n\n"
                    "  output:\n"
                    "    result is number"
                ),
            )
        ) from err

    if result.returncode != 0 and not result.stdout:
        secret_values = collect_secret_values()
        stderr = redact_text(result.stderr or "", secret_values)
        raise Namel3ssError(
            build_guidance_message(
                what="Python tool process failed.",
                why=stderr.strip() or "The tool subprocess exited with an error.",
                fix="Check the tool module and dependencies.",
                example="n3 deps status",
            )
        )
    try:
        parsed = json.loads(result.stdout)
    except json.JSONDecodeError as err:
        raise Namel3ssError(
            build_guidance_message(
                what="Python tool returned invalid JSON.",
                why=str(err),
                fix="Ensure the tool returns JSON-serializable data.",
                example="return {\"ok\": true}",
            )
        ) from err
    if not isinstance(parsed, dict) or "ok" not in parsed:
        raise Namel3ssError(
            build_guidance_message(
                what="Python tool returned unexpected output.",
                why="Tool subprocess output did not match the expected schema.",
                fix="Ensure the tool returns a JSON object.",
                example="return {\"value\": 1}",
            )
        )
    checks = parsed.get("capability_checks")
    checks_list = checks if isinstance(checks, list) else None
    if not parsed.get("ok"):
        error = parsed.get("error") or {}
        return ToolSubprocessResult(
            ok=False,
            output=None,
            error_type=str(error.get("type") or parsed.get("error_type") or "ToolError"),
            error_message=str(error.get("message") or parsed.get("error_message") or "Tool error"),
            capability_checks=checks_list,
        )
    result = parsed.get("result", parsed.get("output"))
    return ToolSubprocessResult(
        ok=True,
        output=result,
        error_type=None,
        error_message=None,
        capability_checks=checks_list,
    )


def _build_env(app_root: Path, *, extra_paths: list[Path] | None) -> dict[str, str]:
    env = os.environ.copy()
    python_path = env.get("PYTHONPATH", "")
    package_root = Path(__file__).resolve().parents[3]
    parts = [str(path) for path in (extra_paths or []) if path.exists()]
    parts.extend([str(app_root), str(package_root)])
    if python_path:
        parts.append(python_path)
    env["PYTHONPATH"] = os.pathsep.join(parts)
    env.setdefault("PYTHONIOENCODING", "utf-8")
    return env


__all__ = ["PROTOCOL_VERSION", "ToolSubprocessResult", "run_tool_subprocess"]
