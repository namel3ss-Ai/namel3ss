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


def _json_default(value):
    if isinstance(value, Decimal):
        if value == value.to_integral_value():
            return int(value)
        text = format(value.normalize(), "f")
        return text
    raise TypeError(f"Object of type {type(value)} is not JSON serializable")


def _main():
    try:
        payload = json.load(sys.stdin)
    except Exception as err:
        sys.stdout.write(json.dumps({"ok": False, "error": {"type": err.__class__.__name__, "message": str(err)}, "protocol_version": 1}))
        return 1
    entry = payload.get("entry")
    args = payload.get("payload")
    protocol_version = payload.get("protocol_version", 1)
    if not isinstance(entry, str):
        sys.stdout.write(json.dumps({"ok": False, "error": {"type": "ValueError", "message": "Missing entry"}, "protocol_version": protocol_version}))
        return 1
    try:
        module_path, function_name = entry.split(":", 1)
    except ValueError:
        sys.stdout.write(json.dumps({"ok": False, "error": {"type": "ValueError", "message": "Invalid entry"}, "protocol_version": protocol_version}))
        return 1
    try:
        module = importlib.import_module(module_path)
        func = getattr(module, function_name)
        if not callable(func):
            raise TypeError("Entry target is not callable")
        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()
        with contextlib.redirect_stdout(stdout_buf), contextlib.redirect_stderr(stderr_buf):
            result = func(args)
        output = {"ok": True, "result": result, "protocol_version": protocol_version}
    except Exception as err:
        output = {"ok": False, "error": {"type": err.__class__.__name__, "message": str(err)}, "protocol_version": protocol_version}
    try:
        sys.stdout.write(json.dumps(output, default=_json_default))
        return 0
    except Exception as err:
        fallback = {"ok": False, "error": {"type": err.__class__.__name__, "message": str(err)}, "protocol_version": protocol_version}
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


def run_tool_subprocess(
    *,
    python_path: Path,
    tool_name: str,
    entry: str,
    payload: dict,
    app_root: Path,
    timeout_seconds: int,
    extra_paths: list[Path] | None = None,
) -> ToolSubprocessResult:
    request = {
        "protocol_version": PROTOCOL_VERSION,
        "tool": tool_name,
        "entry": entry,
        "payload": payload,
    }
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
    if not parsed.get("ok"):
        error = parsed.get("error") or {}
        return ToolSubprocessResult(
            ok=False,
            output=None,
            error_type=str(error.get("type") or parsed.get("error_type") or "ToolError"),
            error_message=str(error.get("message") or parsed.get("error_message") or "Tool error"),
        )
    result = parsed.get("result", parsed.get("output"))
    return ToolSubprocessResult(ok=True, output=result, error_type=None, error_message=None)


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
