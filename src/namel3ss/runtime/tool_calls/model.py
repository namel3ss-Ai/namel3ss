from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class ToolDeclaration:
    name: str
    description: Optional[str] = None
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Optional[Dict[str, Any]] = None
    strict: bool = False


@dataclass(frozen=True)
class ToolCallRequest:
    tool_call_id: str
    tool_name: str
    arguments: Dict[str, Any]
    raw_arguments_text: Optional[str] = None


@dataclass(frozen=True)
class ToolCallResult:
    tool_call_id: str
    tool_name: str
    ok: bool
    output: Any = None
    error_type: Optional[str] = None
    error_message: Optional[str] = None


@dataclass(frozen=True)
class ToolCallPolicy:
    allow_tools: bool = True
    max_calls: int = 3
    strict_json: bool = True
    retry_on_parse_error: bool = False
    max_total_turns: int = 6
