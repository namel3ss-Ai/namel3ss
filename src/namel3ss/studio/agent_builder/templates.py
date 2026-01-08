from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable


@dataclass(frozen=True)
class MemoryPreset:
    key: str
    label: str
    short_term: int
    semantic: bool
    profile: bool


@dataclass(frozen=True)
class PatternSpec:
    pattern_id: str
    label: str
    description: str
    roles: tuple[str, ...]
    requires_tools: bool = False


MEMORY_PRESETS: dict[str, MemoryPreset] = {
    "minimal": MemoryPreset("minimal", "Minimal", 0, False, False),
    "short_term": MemoryPreset("short_term", "Short-term", 3, False, False),
    "semantic": MemoryPreset("semantic", "Semantic", 3, True, False),
    "full": MemoryPreset("full", "Full", 5, True, True),
}

PATTERNS: dict[str, PatternSpec] = {
    "router": PatternSpec(
        pattern_id="router",
        label="Router",
        description="Route requests to specialized agents using deterministic rules.",
        roles=("billing", "sales", "support"),
    ),
    "planner_executor": PatternSpec(
        pattern_id="planner_executor",
        label="Planner / Executor",
        description="Generate a plan, then execute it deterministically.",
        roles=("planner", "executor"),
    ),
    "reviewer_critic": PatternSpec(
        pattern_id="reviewer_critic",
        label="Reviewer / Critic",
        description="Draft a response, then critique before returning.",
        roles=("drafter", "reviewer"),
    ),
    "parallel_coordinator": PatternSpec(
        pattern_id="parallel_coordinator",
        label="Parallel Coordinator",
        description="Run agents in parallel and merge with a stable policy.",
        roles=("worker_one", "worker_two", "worker_three"),
    ),
    "safe_action_tool_first": PatternSpec(
        pattern_id="safe_action_tool_first",
        label="Safe Action (Tool-First)",
        description="Use tools for deterministic effects; AI only proposes.",
        roles=("planner",),
        requires_tools=True,
    ),
}


def list_pattern_metadata() -> list[dict]:
    ordered = sorted(PATTERNS.values(), key=lambda spec: spec.pattern_id)
    return [
        {
            "id": spec.pattern_id,
            "label": spec.label,
            "description": spec.description,
            "roles": list(spec.roles),
            "requires_tools": spec.requires_tools,
        }
        for spec in ordered
    ]


def list_memory_presets() -> list[dict]:
    ordered = sorted(MEMORY_PRESETS.values(), key=lambda preset: preset.key)
    return [
        {
            "id": preset.key,
            "label": preset.label,
            "short_term": preset.short_term,
            "semantic": preset.semantic,
            "profile": preset.profile,
        }
        for preset in ordered
    ]


def memory_preset(key: str) -> MemoryPreset:
    return MEMORY_PRESETS.get(key) or MEMORY_PRESETS["minimal"]


def render_ai_block(
    *,
    name: str,
    provider: str,
    model: str,
    system_prompt: str,
    tools: Iterable[str],
    memory: MemoryPreset,
) -> list[str]:
    lines = [f'ai "{name}":']
    lines.append(f"  provider is \"{provider}\"")
    lines.append(f"  model is \"{model}\"")
    lines.append(f"  system_prompt is \"{system_prompt}\"")
    tool_list = [tool for tool in tools if tool]
    if tool_list:
        lines.append("  tools:")
        for tool in sorted(tool_list):
            lines.append(f"    expose {_quote_string(tool)}")
    lines.append("  memory:")
    lines.append(f"    short_term is {memory.short_term}")
    lines.append(f"    semantic is {'true' if memory.semantic else 'false'}")
    lines.append(f"    profile is {'true' if memory.profile else 'false'}")
    return lines


def render_agent_block(*, name: str, ai_name: str, system_prompt: str) -> list[str]:
    return [
        f'agent "{name}":',
        f"  ai is \"{ai_name}\"",
        f"  system_prompt is \"{system_prompt}\"",
    ]


def render_router_flow(*, flow_name: str, roles: dict[str, str]) -> list[str]:
    billing = roles["billing"]
    sales = roles["sales"]
    support = roles["support"]
    lines = [f'flow "{flow_name}":']
    lines.append("  let topic is input.topic")
    lines.append("  let message is input.message")
    lines.append("  if topic is \"billing\":")
    lines.append(f"    run agent \"{billing}\" with input: message as reply")
    lines.append("    return reply")
    lines.append("  if topic is \"sales\":")
    lines.append(f"    run agent \"{sales}\" with input: message as reply")
    lines.append("    return reply")
    lines.append(f"  run agent \"{support}\" with input: message as reply")
    lines.append("  return reply")
    return lines


def render_planner_executor_flow(*, flow_name: str, roles: dict[str, str]) -> list[str]:
    planner = roles["planner"]
    executor = roles["executor"]
    lines = [f'flow "{flow_name}":']
    lines.append("  let task is input.task")
    lines.append(f"  run agent \"{planner}\" with input: task as plan")
    lines.append(f"  run agent \"{executor}\" with input: plan as result")
    lines.append("  return result")
    return lines


def render_reviewer_flow(*, flow_name: str, roles: dict[str, str]) -> list[str]:
    drafter = roles["drafter"]
    reviewer = roles["reviewer"]
    lines = [f'flow "{flow_name}":']
    lines.append("  let request is input.request")
    lines.append(f"  run agent \"{drafter}\" with input: request as draft")
    lines.append(f"  run agent \"{reviewer}\" with input: draft as review")
    lines.append("  return review")
    return lines


def render_parallel_flow(*, flow_name: str, roles: dict[str, str]) -> list[str]:
    lines = [f'flow "{flow_name}":']
    lines.append("  let task is input.task")
    lines.append("  run agents in parallel:")
    lines.append(f"    agent \"{roles['worker_one']}\" with input: task")
    lines.append(f"    agent \"{roles['worker_two']}\" with input: task")
    lines.append(f"    agent \"{roles['worker_three']}\" with input: task")
    lines.append("  as results")
    lines.append("  let merged is list get results at 0")
    lines.append("  return merged")
    return lines


def render_tool_first_flow(
    *,
    flow_name: str,
    roles: dict[str, str],
    tool_name: str,
    tool_fields: list[str],
) -> list[str]:
    planner = roles["planner"]
    lines = [f'flow "{flow_name}":']
    lines.append("  let request is input.request")
    lines.append(f"  run agent \"{planner}\" with input: request as proposal")
    if tool_fields:
        lines.append(f"  let result is {tool_name}:")
        for field in tool_fields:
            expr = _input_expression_for_field(field)
            lines.append(f"    {field} is {expr}")
    else:
        lines.append(f"  let result is {tool_name}:")
    lines.append("  return result")
    return lines


def render_pattern_flow(
    *,
    pattern_id: str,
    flow_name: str,
    roles: dict[str, str],
    tool_name: str | None,
    tool_fields: list[str],
) -> list[str]:
    if pattern_id == "router":
        return render_router_flow(flow_name=flow_name, roles=roles)
    if pattern_id == "planner_executor":
        return render_planner_executor_flow(flow_name=flow_name, roles=roles)
    if pattern_id == "reviewer_critic":
        return render_reviewer_flow(flow_name=flow_name, roles=roles)
    if pattern_id == "parallel_coordinator":
        return render_parallel_flow(flow_name=flow_name, roles=roles)
    if pattern_id == "safe_action_tool_first":
        if not tool_name:
            raise ValueError("tool_name is required for tool-first pattern")
        return render_tool_first_flow(
            flow_name=flow_name,
            roles=roles,
            tool_name=tool_name,
            tool_fields=tool_fields,
        )
    raise ValueError(f"Unknown pattern '{pattern_id}'")


def render_pattern_snippet(
    *,
    pattern_id: str,
    ai_block: list[str] | None,
    agent_blocks: list[list[str]],
    flow_lines: list[str],
) -> str:
    lines: list[str] = []
    if ai_block:
        lines.extend(ai_block)
        lines.append("")
    for block in agent_blocks:
        lines.extend(block)
        lines.append("")
    lines.extend(flow_lines)
    return "\n".join(lines).rstrip() + "\n"


def _input_expression_for_field(field: str) -> str:
    if _is_identifier(field):
        return f"input.{field}"
    return f'map get input key "{field}"'


def _is_identifier(value: str) -> bool:
    return bool(re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", value))


def _quote_string(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


__all__ = [
    "MEMORY_PRESETS",
    "PATTERNS",
    "PatternSpec",
    "MemoryPreset",
    "list_pattern_metadata",
    "list_memory_presets",
    "memory_preset",
    "render_ai_block",
    "render_agent_block",
    "render_pattern_flow",
    "render_pattern_snippet",
]
