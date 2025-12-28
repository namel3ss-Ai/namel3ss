from __future__ import annotations

import json
import time
from typing import Callable, Dict, List

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.tool_calls.model import ToolCallPolicy, ToolDeclaration
from namel3ss.runtime.tool_calls.parse import parse_tool_call_response
from namel3ss.runtime.tool_calls.provider_iface import AssistantError, AssistantText, AssistantToolCall, ProviderAdapter
from namel3ss.traces.builders import (
    build_tool_call_completed,
    build_tool_call_failed,
    build_tool_call_requested,
)


def run_ai_tool_pipeline(
    *,
    adapter: ProviderAdapter,
    call_id: str,
    provider_name: str,
    model: str,
    messages: List[dict],
    tools: List[ToolDeclaration],
    policy: ToolCallPolicy,
    tool_executor: Callable[[str, Dict[str, object]], Dict[str, object]],
    canonical_events: List[dict],
    tool_events: List[dict],
) -> str:
    tool_map: Dict[str, ToolDeclaration] = {tool.name: tool for tool in tools}
    tool_call_count = 0
    turns = 0
    while True:
        turns += 1
        if turns > policy.max_total_turns:
            raise Namel3ssError("AI exceeded maximum turns while calling tools")
        response = adapter.run_model(messages, tools, policy)
        if isinstance(response, AssistantText):
            return response.text
        if isinstance(response, AssistantError):
            raise Namel3ssError(f"AI provider error: {response.error_message}")
        if not policy.allow_tools:
            raise Namel3ssError("Tool calls are not allowed by policy")
        if not isinstance(response, AssistantToolCall):
            raise Namel3ssError("AI provider returned unexpected response")
        tool_call_count += 1
        if tool_call_count > policy.max_calls:
            raise Namel3ssError("AI exceeded maximum tool calls")
        tool_start = time.monotonic()
        canonical_events.append(
            build_tool_call_requested(
                call_id=call_id,
                tool_call_id=response.tool_call_id,
                provider=provider_name,
                model=model,
                tool_name=response.tool_name,
                arguments=response.arguments_json_text,
            )
        )
        try:
            request = parse_tool_call_response(
                tool_call_id=response.tool_call_id,
                tool_name=response.tool_name,
                arguments_json_text=response.arguments_json_text,
                tools=tool_map,
                policy=policy,
            )
        except Namel3ssError as err:
            duration_ms = int((time.monotonic() - tool_start) * 1000)
            canonical_events.append(
                build_tool_call_failed(
                    call_id=call_id,
                    tool_call_id=response.tool_call_id,
                    provider=provider_name,
                    model=model,
                    tool_name=response.tool_name,
                    error_type=err.__class__.__name__,
                    error_message=str(err),
                    duration_ms=duration_ms,
                )
            )
            raise
        tool_events.append(
            {
                "type": "call",
                "name": request.tool_name,
                "args": request.arguments,
                "tool_call_id": request.tool_call_id,
            }
        )
        try:
            result = tool_executor(request.tool_name, request.arguments)
        except Namel3ssError as err:
            duration_ms = int((time.monotonic() - tool_start) * 1000)
            canonical_events.append(
                build_tool_call_failed(
                    call_id=call_id,
                    tool_call_id=request.tool_call_id,
                    provider=provider_name,
                    model=model,
                    tool_name=request.tool_name,
                    error_type=err.__class__.__name__,
                    error_message=str(err),
                    duration_ms=duration_ms,
                )
            )
            raise
        except Exception as err:  # pragma: no cover - defensive
            duration_ms = int((time.monotonic() - tool_start) * 1000)
            canonical_events.append(
                build_tool_call_failed(
                    call_id=call_id,
                    tool_call_id=request.tool_call_id,
                    provider=provider_name,
                    model=model,
                    tool_name=request.tool_name,
                    error_type=err.__class__.__name__,
                    error_message=str(err),
                    duration_ms=duration_ms,
                )
            )
            raise
        duration_ms = int((time.monotonic() - tool_start) * 1000)
        canonical_events.append(
            build_tool_call_completed(
                call_id=call_id,
                tool_call_id=request.tool_call_id,
                provider=provider_name,
                model=model,
                tool_name=request.tool_name,
                result=result,
                duration_ms=duration_ms,
            )
        )
        tool_events.append(
            {
                "type": "result",
                "name": request.tool_name,
                "result": result,
                "tool_call_id": request.tool_call_id,
            }
        )
        try:
            messages.append(
                {
                    "role": "tool",
                    "name": request.tool_name,
                    "tool_call_id": request.tool_call_id,
                    "content": json.dumps(result),
                }
            )
        except Exception:
            messages.append(
                {
                    "role": "tool",
                    "name": request.tool_name,
                    "tool_call_id": request.tool_call_id,
                    "content": str(result),
                }
            )


__all__ = ["run_ai_tool_pipeline"]
