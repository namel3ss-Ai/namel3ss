from __future__ import annotations

from dataclasses import dataclass

from namel3ss.runtime.tools.bindings_yaml import ToolBinding


@dataclass(frozen=True)
class ToolDeclInfo:
    name: str
    kind: str
    input_fields: int
    output_fields: int
    line: int | None
    column: int | None


@dataclass(frozen=True)
class ToolIssue:
    code: str
    message: str
    severity: str
    tool_name: str | None = None
    line: int | None = None
    column: int | None = None
    file: str | None = None


@dataclass(frozen=True)
class PackSummary:
    pack_id: str
    name: str
    version: str
    description: str
    author: str
    license: str
    tools: list[str]
    source: str
    verified: bool
    enabled: bool
    errors: list[str]


@dataclass(frozen=True)
class PackToolSummary:
    tool_name: str
    pack_id: str
    pack_name: str
    pack_version: str
    source: str
    verified: bool
    enabled: bool
    runner: str


@dataclass(frozen=True)
class ToolHealthReport:
    declared_tools: list[ToolDeclInfo]
    bindings: dict[str, ToolBinding]
    pack_tools: dict[str, list[PackToolSummary]]
    pack_collisions: list[str]
    packs: list[PackSummary]
    missing_bindings: list[str]
    unused_bindings: list[str]
    collisions: list[str]
    invalid_bindings: list[str]
    invalid_runners: list[str]
    service_missing_urls: list[str]
    container_missing_images: list[str]
    container_missing_runtime: list[str]
    empty_io: list[str]
    duplicate_decls: list[str]
    issues: list[ToolIssue]
    bindings_valid: bool
    bindings_error: str | None
