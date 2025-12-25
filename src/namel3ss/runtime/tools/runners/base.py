from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from namel3ss.config.model import AppConfig
from namel3ss.runtime.tools.bindings_yaml import ToolBinding


@dataclass(frozen=True)
class ToolRunnerRequest:
    tool_name: str
    kind: str
    entry: str
    payload: object
    timeout_ms: int
    trace_id: str
    app_root: Path
    flow_name: str | None
    binding: ToolBinding
    config: AppConfig
    pack_paths: list[Path] | None = None
    capability_context: dict[str, object] | None = None
    allow_unsafe: bool = False


@dataclass(frozen=True)
class ToolRunnerResult:
    ok: bool
    output: object | None
    error_type: str | None
    error_message: str | None
    metadata: dict[str, object] = field(default_factory=dict)
    capability_checks: list[dict[str, object]] | None = None


class ToolRunner(Protocol):
    name: str

    def execute(self, request: ToolRunnerRequest) -> ToolRunnerResult:
        ...


__all__ = ["ToolRunner", "ToolRunnerRequest", "ToolRunnerResult"]
