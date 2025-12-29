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


@dataclass(frozen=True)
class NodeSubprocessResult:
    ok: bool
    output: object | None
    error_type: str | None
    error_message: str | None
    capability_checks: list[dict[str, object]] | None = None


def run_node_subprocess(
    *,
    node_path: Path,
    tool_name: str,
    entry: str,
    payload: dict,
    app_root: Path,
    timeout_seconds: int,
    extra_paths: list[Path] | None = None,
    capability_context: dict[str, object] | None = None,
    trace_id: str | None = None,
) -> NodeSubprocessResult:
    request = {
        "protocol_version": PROTOCOL_VERSION,
        "tool": tool_name,
        "entry": entry,
        "payload": payload,
    }
    if extra_paths:
        request["module_paths"] = [str(path) for path in extra_paths if path.exists()]
    if capability_context:
        request["capability_context"] = capability_context
    if trace_id:
        request["trace_id"] = trace_id
    input_text = json_dumps(request)
    env = _build_env(app_root, extra_paths=extra_paths)
    try:
        result = subprocess.run(
            [str(node_path), str(_shim_path())],
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
                what="Node runtime was not found.",
                why=str(err),
                fix="Install Node.js or add it to PATH.",
                example="node --version",
            )
        ) from err
    except subprocess.TimeoutExpired as err:
        raise Namel3ssError(
            build_guidance_message(
                what="Node tool execution timed out.",
                why=f"Tool exceeded {timeout_seconds}s timeout.",
                fix="Increase timeout_seconds or optimize the tool.",
                example="timeout_seconds is 20",
            )
        ) from err
    if result.returncode != 0 and not result.stdout:
        secret_values = collect_secret_values()
        stderr = redact_text(result.stderr or "", secret_values)
        raise Namel3ssError(
            build_guidance_message(
                what="Node tool process failed.",
                why=stderr.strip() or "The tool subprocess exited with an error.",
                fix="Check the tool module and dependencies.",
                example="node --version",
            )
        )
    try:
        parsed = json.loads(result.stdout)
    except json.JSONDecodeError as err:
        raise Namel3ssError(
            build_guidance_message(
                what="Node tool returned invalid JSON.",
                why=str(err),
                fix="Ensure the tool returns JSON-serializable data.",
                example='return { "ok": true }',
            )
        ) from err
    if not isinstance(parsed, dict) or "ok" not in parsed:
        raise Namel3ssError(
            build_guidance_message(
                what="Node tool returned unexpected output.",
                why="Tool subprocess output did not match the expected schema.",
                fix="Ensure the tool returns a JSON object.",
                example='return { "value": 1 }',
            )
        )
    checks = parsed.get("capability_checks")
    checks_list = checks if isinstance(checks, list) else None
    if not parsed.get("ok"):
        error = parsed.get("error") or {}
        return NodeSubprocessResult(
            ok=False,
            output=None,
            error_type=str(error.get("type") or parsed.get("error_type") or "ToolError"),
            error_message=str(error.get("message") or parsed.get("error_message") or "Tool error"),
            capability_checks=checks_list,
        )
    result_value = parsed.get("result", parsed.get("output"))
    return NodeSubprocessResult(
        ok=True,
        output=result_value,
        error_type=None,
        error_message=None,
        capability_checks=checks_list,
    )


def _shim_path() -> Path:
    return Path(__file__).resolve().parent / "shim" / "index.js"


def _build_env(app_root: Path, *, extra_paths: list[Path] | None) -> dict[str, str]:
    env = os.environ.copy()
    node_path = env.get("NODE_PATH", "")
    parts = [str(app_root)]
    if extra_paths:
        parts.extend(str(path) for path in extra_paths if path.exists())
    if node_path:
        parts.append(node_path)
    env["NODE_PATH"] = os.pathsep.join(parts)
    return env


__all__ = ["PROTOCOL_VERSION", "NodeSubprocessResult", "run_node_subprocess"]
