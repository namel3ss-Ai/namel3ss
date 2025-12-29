from __future__ import annotations

import math
import shutil
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.tools.runners.base import ToolRunnerRequest, ToolRunnerResult
from namel3ss.runtime.tools.runners.node.protocol import PROTOCOL_VERSION, run_node_subprocess


class NodeRunner:
    name = "node"

    def execute(self, request: ToolRunnerRequest) -> ToolRunnerResult:
        node_path = _resolve_node_path()
        timeout_seconds = max(1, math.ceil(request.timeout_ms / 1000))
        result = run_node_subprocess(
            node_path=node_path,
            tool_name=request.tool_name,
            entry=request.entry,
            payload=request.payload,
            app_root=request.app_root,
            timeout_seconds=timeout_seconds,
            extra_paths=request.pack_paths,
            capability_context=request.capability_context,
            trace_id=request.trace_id,
        )
        metadata = {
            "runner": self.name,
            "node_path": str(node_path),
            "protocol_version": PROTOCOL_VERSION,
        }
        return ToolRunnerResult(
            ok=result.ok,
            output=result.output,
            error_type=result.error_type,
            error_message=result.error_message,
            metadata=metadata,
            capability_checks=result.capability_checks,
        )


def _resolve_node_path() -> Path:
    path = shutil.which("node")
    if path:
        return Path(path)
    raise Namel3ssError(
        build_guidance_message(
            what="Node runtime was not found.",
            why="The node executable was not found on PATH.",
            fix="Install Node.js or add it to PATH.",
            example="node --version",
        )
    )


__all__ = ["NodeRunner"]
