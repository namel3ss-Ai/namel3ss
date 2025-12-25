from __future__ import annotations

import json
import math
import subprocess

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.tools.python_subprocess import PROTOCOL_VERSION
from namel3ss.runtime.tools.runners.base import ToolRunnerRequest, ToolRunnerResult
from namel3ss.runtime.tools.runners.container_detect import detect_container_runtime


DEFAULT_COMMAND = ["python", "-m", "namel3ss_tools.runner"]


class ContainerRunner:
    name = "container"

    def execute(self, request: ToolRunnerRequest) -> ToolRunnerResult:
        runtime = detect_container_runtime()
        if runtime is None:
            raise Namel3ssError(_missing_runtime_message(request.tool_name))
        image = request.binding.image
        if not image:
            raise Namel3ssError(_missing_image_message(request.tool_name))
        command = request.binding.command or DEFAULT_COMMAND
        env_flags = _env_flags(request.binding.env or {})
        timeout_seconds = max(1, math.ceil(request.timeout_ms / 1000))
        input_text = json.dumps(
            {
                "protocol_version": PROTOCOL_VERSION,
                "tool": request.tool_name,
                "entry": request.entry,
                "payload": request.payload,
            }
        )
        cmd = [runtime, "run", "--rm", "-i", *env_flags, image, *command]
        try:
            result = subprocess.run(
                cmd,
                input=input_text,
                text=True,
                capture_output=True,
                timeout=timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as err:
            raise Namel3ssError(
                build_guidance_message(
                    what="Container tool execution timed out.",
                    why=f"Tool exceeded {timeout_seconds}s timeout.",
                    fix="Increase timeout_seconds or optimize the tool.",
                    example="timeout_seconds is 20",
                )
            ) from err
        if result.returncode != 0 and not result.stdout:
            raise Namel3ssError(
                build_guidance_message(
                    what="Container tool process failed.",
                    why=result.stderr.strip() or "The container exited with an error.",
                    fix="Check the container image and command.",
                    example='image: "ghcr.io/namel3ss/tools:latest"',
                )
            )
        response = _parse_response(result.stdout)
        metadata = {
            "runner": self.name,
            "container_runtime": runtime,
            "image": image,
            "command": " ".join(command),
            "protocol_version": PROTOCOL_VERSION,
        }
        if not response.get("ok"):
            error = response.get("error") or {}
            return ToolRunnerResult(
                ok=False,
                output=None,
                error_type=str(error.get("type") or "ToolError"),
                error_message=str(error.get("message") or "Tool error"),
                metadata=metadata,
            )
        return ToolRunnerResult(
            ok=True,
            output=response.get("result"),
            error_type=None,
            error_message=None,
            metadata=metadata,
        )


def _env_flags(env: dict[str, str]) -> list[str]:
    flags: list[str] = []
    for key, value in sorted(env.items()):
        flags.extend(["-e", f"{key}={value}"])
    return flags


def _parse_response(raw: str) -> dict:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as err:
        raise Namel3ssError(
            build_guidance_message(
                what="Container tool returned invalid JSON.",
                why=str(err),
                fix="Ensure the container runner returns JSON.",
                example='{"ok": true, "result": {"value": 1}}',
            )
        ) from err
    if not isinstance(parsed, dict) or "ok" not in parsed:
        raise Namel3ssError(
            build_guidance_message(
                what="Container tool returned unexpected output.",
                why="Response did not match the tool runner schema.",
                fix="Ensure the container runner returns ok/result or ok/error.",
                example='{"ok": true, "result": {"value": 1}}',
            )
        )
    return parsed


def _missing_runtime_message(tool_name: str) -> str:
    return build_guidance_message(
        what=f'Tool "{tool_name}" requires a container runtime.',
        why="Runner is set to container but docker/podman was not found.",
        fix="Install docker/podman or switch the runner to local/service.",
        example='n3 tools set-runner "tool name" --runner local',
    )


def _missing_image_message(tool_name: str) -> str:
    return build_guidance_message(
        what=f'Tool "{tool_name}" requires a container image.',
        why="Runner is set to container but no image was provided.",
        fix="Set image in .namel3ss/tools.yaml.",
        example=(
            "tools:\n"
            f'  "{tool_name}":\n'
            '    kind: "python"\n'
            '    entry: "tools.my_tool:run"\n'
            '    runner: "container"\n'
            '    image: "ghcr.io/namel3ss/tools:latest"'
        ),
    )


__all__ = ["ContainerRunner"]
