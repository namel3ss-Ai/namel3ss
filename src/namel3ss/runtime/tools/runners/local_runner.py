from __future__ import annotations

import math

from namel3ss.runtime.tools.python_env import detect_dependency_info, resolve_python_env
from namel3ss.runtime.tools.python_subprocess import PROTOCOL_VERSION, run_tool_subprocess
from namel3ss.runtime.tools.runners.base import ToolRunnerRequest, ToolRunnerResult


class LocalRunner:
    name = "local"

    def execute(self, request: ToolRunnerRequest) -> ToolRunnerResult:
        env_info = resolve_python_env(request.app_root)
        dep_info = detect_dependency_info(request.app_root)
        timeout_seconds = max(1, math.ceil(request.timeout_ms / 1000))
        result = run_tool_subprocess(
            python_path=env_info.python_path,
            tool_name=request.tool_name,
            entry=request.entry,
            payload=request.payload,
            app_root=request.app_root,
            timeout_seconds=timeout_seconds,
            extra_paths=request.pack_paths,
            capability_context=request.capability_context,
            sandbox=bool(getattr(request.binding, "sandbox", False)),
            trace_id=request.trace_id,
        )
        metadata = {
            "runner": self.name,
            "python_env": env_info.env_kind,
            "python_path": str(env_info.python_path),
            "deps_source": dep_info.kind,
            "protocol_version": PROTOCOL_VERSION,
            "sandbox": bool(getattr(request.binding, "sandbox", False)),
        }
        return ToolRunnerResult(
            ok=result.ok,
            output=result.output,
            error_type=result.error_type,
            error_message=result.error_message,
            metadata=metadata,
            capability_checks=result.capability_checks,
        )


__all__ = ["LocalRunner"]
