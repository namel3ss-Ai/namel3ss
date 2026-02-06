from __future__ import annotations

import json
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.sandbox.config import SandboxFlow, load_sandbox_config
from namel3ss.runtime.tools.runners.container_detect import detect_container_runtime


DEFAULT_BASE_IMAGE = "python:3.11-slim"


@dataclass(frozen=True)
class SandboxResult:
    ok: bool
    result: object | None
    error_type: str | None
    error_message: str | None
    runner: str

    def as_dict(self) -> dict:
        payload = {
            "ok": self.ok,
            "runner": self.runner,
        }
        if self.ok:
            payload["result"] = self.result
        else:
            payload["error"] = {
                "type": self.error_type or "SandboxError",
                "message": self.error_message or "Sandbox error",
            }
        return payload


def build_sandbox_image(
    *,
    project_root: str | Path | None,
    app_path: str | Path | None,
    flow_name: str,
) -> str:
    config = load_sandbox_config(project_root, app_path)
    flow = config.flow_for(flow_name)
    if flow is None:
        raise Namel3ssError(_missing_flow_message(flow_name))
    runtime = detect_container_runtime()
    if runtime is None:
        return "Container runtime not found. Using local sandbox runner."
    image = flow.image or DEFAULT_BASE_IMAGE
    try:
        subprocess.run([runtime, "pull", image], check=False, capture_output=True, text=True)
    except Exception:
        return f"Container runtime detected but could not pull {image}."
    return f"Sandbox image ready: {image}"


def run_sandbox_flow(
    *,
    project_root: str | Path | None,
    app_path: str | Path | None,
    flow_name: str,
    payload: dict,
) -> dict:
    config = load_sandbox_config(project_root, app_path)
    flow = config.flow_for(flow_name)
    if flow is None:
        raise Namel3ssError(_missing_flow_message(flow_name))
    runtime = detect_container_runtime()
    if runtime:
        result = _run_container(runtime, flow, payload, project_root)
        return result.as_dict()
    result = _run_local(flow, payload)
    return result.as_dict()


def _run_container(runtime: str, flow: SandboxFlow, payload: dict, project_root: str | Path | None) -> SandboxResult:
    image = flow.image or DEFAULT_BASE_IMAGE
    command = _container_command(flow)
    args = [runtime, "run", "--rm", "-i"]
    if not flow.allow_network:
        args.extend(["--network", "none"])
    if flow.cpu_seconds is not None:
        args.extend(["--cpus", str(flow.cpu_seconds)])
    if flow.memory_mb is not None:
        args.extend(["--memory", f"{flow.memory_mb}m"])
    if project_root:
        root = Path(project_root)
        args.extend(["-v", f"{root.as_posix()}:/workspace", "-w", "/workspace"])
    args.append(image)
    args.extend(command)
    return _run_subprocess(args, payload, timeout_seconds=flow.timeout_seconds, runner="container")


def _run_local(flow: SandboxFlow, payload: dict) -> SandboxResult:
    args = _local_command(flow)
    return _run_subprocess(args, payload, timeout_seconds=flow.timeout_seconds, runner="local")


def _run_subprocess(args: list[str], payload: dict, *, timeout_seconds: int | None, runner: str) -> SandboxResult:
    input_text = json.dumps(payload)
    try:
        result = subprocess.run(
            args,
            input=input_text,
            text=True,
            capture_output=True,
            timeout=timeout_seconds if timeout_seconds else None,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return SandboxResult(
            ok=False,
            result=None,
            error_type="TimeoutError",
            error_message="Sandbox execution exceeded the timeout.",
            runner=runner,
        )
    if result.returncode != 0 and not result.stdout:
        return SandboxResult(
            ok=False,
            result=None,
            error_type="SandboxError",
            error_message=result.stderr.strip() or "Sandbox execution failed.",
            runner=runner,
        )
    try:
        parsed = json.loads(result.stdout)
    except json.JSONDecodeError:
        return SandboxResult(
            ok=False,
            result=None,
            error_type="SandboxError",
            error_message="Sandbox returned invalid JSON.",
            runner=runner,
        )
    if not isinstance(parsed, dict):
        return SandboxResult(
            ok=False,
            result=None,
            error_type="SandboxError",
            error_message="Sandbox returned an unexpected payload.",
            runner=runner,
        )
    if "ok" in parsed:
        if not parsed.get("ok"):
            error = parsed.get("error") if isinstance(parsed.get("error"), dict) else {}
            return SandboxResult(
                ok=False,
                result=None,
                error_type=str(error.get("type") or "SandboxError"),
                error_message=str(error.get("message") or "Sandbox error"),
                runner=runner,
            )
        result = parsed.get("result")
        if result is None and "outputs" in parsed:
            result = parsed.get("outputs")
        return SandboxResult(
            ok=True,
            result=result,
            error_type=None,
            error_message=None,
            runner=runner,
        )
    if "error" in parsed:
        error = parsed.get("error") if isinstance(parsed.get("error"), dict) else {}
        return SandboxResult(
            ok=False,
            result=None,
            error_type=str(error.get("type") or "SandboxError"),
            error_message=str(error.get("message") or "Sandbox error"),
            runner=runner,
        )
    result = parsed.get("outputs") if "outputs" in parsed else parsed
    return SandboxResult(
        ok=True,
        result=result,
        error_type=None,
        error_message=None,
        runner=runner,
    )


def _python_runner_command(entry: str) -> list[str]:
    return ["python", "-c", _runner_script(entry)]


def _container_command(flow: SandboxFlow) -> list[str]:
    if flow.command:
        return _split_command(flow.command)
    if flow.entry and _looks_like_python_entry(flow.entry):
        return _python_runner_command(flow.entry)
    if flow.entry:
        return _split_command(flow.entry)
    raise Namel3ssError("Sandbox entry is missing a command.")


def _local_command(flow: SandboxFlow) -> list[str]:
    if flow.command:
        return _split_command(flow.command)
    if flow.entry and _looks_like_python_entry(flow.entry):
        return [sys.executable, "-c", _runner_script(flow.entry)]
    if flow.entry:
        return _split_command(flow.entry)
    raise Namel3ssError("Sandbox entry is missing a command.")


def _looks_like_python_entry(entry: str) -> bool:
    if ":" not in entry:
        return False
    if any(ch.isspace() for ch in entry):
        return False
    return True


def _split_command(command: str) -> list[str]:
    parts = shlex.split(command)
    if not parts:
        return [command]
    return parts


def _runner_script(entry: str) -> str:
    return (
        "import json,importlib,sys; "
        "payload=json.load(sys.stdin); "
        f"mod,fn='{entry}'.split(':',1); "
        "func=getattr(importlib.import_module(mod), fn); "
        "result=func(payload); "
        "print(json.dumps({'ok': True, 'result': result}))"
    )


def _missing_flow_message(flow_name: str) -> str:
    return build_guidance_message(
        what=f"No sandbox configuration found for '{flow_name}'.",
        why="The flow is not listed in .namel3ss/sandbox.yaml.",
        fix="Add the flow to sandbox.yaml or run without sandbox.",
        example='sandboxes:\n  summarize:\n    entry: "plugins.summarize:run"',
    )


__all__ = ["SandboxResult", "build_sandbox_image", "run_sandbox_flow"]
