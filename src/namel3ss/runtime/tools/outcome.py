from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ToolDecision:
    status: str
    capability: str | None
    reason: str
    message: str


@dataclass(frozen=True)
class ToolCallOutcome:
    tool_name: str
    decision: ToolDecision
    result_kind: str
    result_summary: str
    # result_value carries the tool output for runtime use only.
    result_value: object | None = field(default=None, repr=False, compare=False)


__all__ = ["ToolCallOutcome", "ToolDecision"]
