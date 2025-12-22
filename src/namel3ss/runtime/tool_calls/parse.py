from __future__ import annotations

import json
from typing import Dict, List

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.tool_calls.model import ToolCallPolicy, ToolCallRequest, ToolDeclaration


def parse_tool_call_response(
    tool_call_id: str,
    tool_name: str,
    arguments_json_text: str,
    tools: Dict[str, ToolDeclaration],
    policy: ToolCallPolicy,
) -> ToolCallRequest:
    tool_decl = tools.get(tool_name)
    if tool_decl is None:
        raise Namel3ssError(f"AI requested unknown tool '{tool_name}'")
    raw_text = arguments_json_text if isinstance(arguments_json_text, str) else str(arguments_json_text)
    try:
        parsed_args = json.loads(raw_text)
    except json.JSONDecodeError as err:
        message = f"Invalid tool arguments JSON for '{tool_name}': {err.msg}"
        if policy.retry_on_parse_error:
            raise Namel3ssError(message)
        raise Namel3ssError(message)
    if not isinstance(parsed_args, dict):
        raise Namel3ssError(f"Tool arguments for '{tool_name}' must be a JSON object")
    raw_preview = raw_text if len(raw_text) <= 200 else raw_text[:200] + "... (truncated)"
    return ToolCallRequest(
        tool_call_id=tool_call_id,
        tool_name=tool_decl.name,
        arguments=parsed_args,
        raw_arguments_text=raw_preview,
    )


__all__: List[str] = ["parse_tool_call_response"]
