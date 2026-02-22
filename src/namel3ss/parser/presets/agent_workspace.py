from __future__ import annotations

from dataclasses import dataclass
from typing import Final


AGENT_WORKSPACE_PATTERN_SINGLE_AGENT: Final[str] = "single_agent"
AGENT_WORKSPACE_PATTERN_ROUTER_SPECIALISTS: Final[str] = "router_specialists"
AGENT_WORKSPACE_PATTERN_PLANNER_EXECUTOR: Final[str] = "planner_executor"
AGENT_WORKSPACE_PATTERN_RESEARCH_RAG: Final[str] = "research_rag"
SUPPORTED_AGENT_WORKSPACE_PATTERNS: Final[tuple[str, ...]] = (
    AGENT_WORKSPACE_PATTERN_SINGLE_AGENT,
    AGENT_WORKSPACE_PATTERN_ROUTER_SPECIALISTS,
    AGENT_WORKSPACE_PATTERN_PLANNER_EXECUTOR,
    AGENT_WORKSPACE_PATTERN_RESEARCH_RAG,
)
SUPPORTED_AGENT_WORKSPACE_OVERRIDE_FLOWS: Final[tuple[str, ...]] = (
    "agent.route",
    "agent.retrieve",
    "agent.answer",
    "agent.tool_policy",
    "agent.fallback",
    "agent.citations.format",
)
DEFAULT_AGENT_WORKSPACE_MODEL: Final[str] = "gpt-4o-mini"
DEFAULT_AGENT_WORKSPACE_TEMPERATURE: Final[float] = 0.2
DEFAULT_AGENT_WORKSPACE_SYSTEM_PROMPT: Final[str] = (
    "You are a grounded assistant. Use only provided context. "
    "If context is empty, clearly say grounded evidence is unavailable."
)
DEFAULT_AGENT_WORKSPACE_FALLBACK_MESSAGE: Final[str] = (
    "No grounded support found in indexed sources for this query."
)
AGENT_WORKSPACE_INTERNAL_AI_NAME: Final[str] = "__agent_workspace_ai"


@dataclass(frozen=True)
class AgentWorkspacePresetConfig:
    title: str = "Agent Workspace"
    model: str = DEFAULT_AGENT_WORKSPACE_MODEL
    system: str | None = None
    temperature: float = DEFAULT_AGENT_WORKSPACE_TEMPERATURE
    pattern: str = AGENT_WORKSPACE_PATTERN_SINGLE_AGENT


def render_agent_workspace_source(
    *,
    spec_line: str,
    config: AgentWorkspacePresetConfig,
    override_bodies: dict[str, list[str]] | None = None,
) -> str:
    model = _escape_string(config.model or DEFAULT_AGENT_WORKSPACE_MODEL)
    system_prompt = _escape_string(config.system or DEFAULT_AGENT_WORKSPACE_SYSTEM_PROMPT)
    title = _escape_string(config.title)
    pattern = _escape_string(config.pattern or AGENT_WORKSPACE_PATTERN_SINGLE_AGENT)
    fallback_message = _escape_string(DEFAULT_AGENT_WORKSPACE_FALLBACK_MESSAGE)
    overrides = dict(override_bodies or {})

    lines: list[str] = [
        spec_line,
        "",
        f'ai "{AGENT_WORKSPACE_INTERNAL_AI_NAME}":',
        '  provider is "openai"',
        f'  model is "{model}"',
        f'  system_prompt is "{system_prompt}"',
        "  memory:",
        "    short_term is 0",
        "    semantic is false",
        "    profile is false",
        "",
        'agent "assistant":',
        f'  ai is "{AGENT_WORKSPACE_INTERNAL_AI_NAME}"',
        '  system_prompt is "Handle user requests with deterministic structure."',
        "",
        'contract flow "agent.route":',
        "  input:",
        "    message is text",
        "    context is optional text",
        "  output:",
        "    route is text",
        "    query is text",
        "    context is text",
        "",
        'contract flow "agent.retrieve":',
        "  input:",
        "    query is text",
        "    context is optional text",
        "  output:",
        "    context is text",
        "    citations is json",
        "",
        'contract flow "agent.tool_policy":',
        "  input:",
        "    tool_name is text",
        "  output:",
        "    allowed is boolean",
        "    reason is text",
        "",
        'contract flow "agent.fallback":',
        "  input:",
        "    message is text",
        "    context is optional text",
        "    error_text is optional text",
        "  output:",
        "    answer_text is text",
        "    citations is json",
        "",
        'contract flow "agent.citations.format":',
        "  input:",
        "    citations is json",
        "  output:",
        "    citations is json",
        "",
        'contract flow "agent.answer":',
        "  input:",
        "    message is text",
        "    context is optional text",
        "  output:",
        "    answer_text is text",
        "    citations is json",
        "",
    ]

    lines.extend(
        _render_flow_block(
            flow_name="agent.route",
            override_bodies=overrides,
            default_body=_default_agent_route_lines(pattern=pattern),
        )
    )
    lines.extend(
        _render_flow_block(
            flow_name="agent.retrieve",
            override_bodies=overrides,
            default_body=_default_agent_retrieve_lines(),
        )
    )
    lines.extend(
        _render_flow_block(
            flow_name="agent.tool_policy",
            override_bodies=overrides,
            default_body=_default_agent_tool_policy_lines(),
        )
    )
    lines.extend(
        _render_flow_block(
            flow_name="agent.fallback",
            override_bodies=overrides,
            default_body=_default_agent_fallback_lines(fallback_message=fallback_message),
        )
    )
    lines.extend(
        _render_flow_block(
            flow_name="agent.citations.format",
            override_bodies=overrides,
            default_body=_default_agent_citations_format_lines(),
        )
    )
    lines.extend(
        _render_flow_block(
            flow_name="agent.answer",
            override_bodies=overrides,
            default_body=_default_agent_answer_lines(),
        )
    )

    lines.extend(
        [
            'flow "agent.demo": requires true',
            '  let answer_result is call flow "agent.answer":',
            "    input:",
            '      message is "Describe the current workspace context."',
            '      context is ""',
            "    output:",
            "      answer_text",
            "      citations",
            '  return map get answer_result key "answer_text"',
            "",
            f'page "home": requires true',
            f'  title is "{title}"',
            '  text is "Agent workspace preset: deterministic routing, retrieval, and answer contracts."',
            '  button "Run demo":',
            '    calls flow "agent.demo"',
            "",
        ]
    )

    return "\n".join(lines).rstrip() + "\n"


def _render_flow_block(
    *,
    flow_name: str,
    override_bodies: dict[str, list[str]],
    default_body: list[str],
) -> list[str]:
    body = override_bodies.get(flow_name)
    if body is None:
        return list(default_body)
    return [f'flow "{flow_name}": requires true', *_indent_lines(body), ""]


def _default_agent_route_lines(*, pattern: str) -> list[str]:
    return [
        'flow "agent.route": requires true',
        f'  let route is "{pattern}"',
        "  let query is input.message",
        '  let context_text is ""',
        "  try:",
        "    let provided_context is input.context",
        '    if provided_context is not "":',
        "      set context_text is provided_context",
        "  with catch err:",
        "    set context_text is context_text",
        "  return map:",
        '    "route" is route',
        '    "query" is query',
        '    "context" is context_text',
        "",
    ]


def _default_agent_retrieve_lines() -> list[str]:
    return [
        'flow "agent.retrieve": requires true',
        '  let context_text is ""',
        "  try:",
        "    let provided_context is input.context",
        '    if provided_context is not "":',
        "      set context_text is provided_context",
        "  with catch err:",
        "    set context_text is context_text",
        "  return map:",
        '    "context" is context_text',
        '    "citations" is list:',
        "",
    ]


def _default_agent_tool_policy_lines() -> list[str]:
    return [
        'flow "agent.tool_policy": requires true',
        "  return map:",
        '    "allowed" is true',
        '    "reason" is "allowed"',
        "",
    ]


def _default_agent_fallback_lines(*, fallback_message: str) -> list[str]:
    return [
        'flow "agent.fallback": requires true',
        '  let context_text is ""',
        "  try:",
        "    let provided_context is input.context",
        '    if provided_context is not "":',
        "      set context_text is provided_context",
        "  with catch err:",
        "    set context_text is context_text",
        '  if context_text is "":',
        "    return map:",
        f'      "answer_text" is "{fallback_message}"',
        '      "citations" is list:',
        "  return map:",
        '    "answer_text" is "Grounded support is available. Open View Sources to inspect evidence."',
        '    "citations" is list:',
        "      map:",
        '        "index" is 1',
        '        "title" is "Attached context"',
        '        "source_id" is "attached-context"',
        "",
    ]


def _default_agent_citations_format_lines() -> list[str]:
    return [
        'flow "agent.citations.format": requires true',
        "  return map:",
        '    "citations" is input.citations',
        "",
    ]


def _default_agent_answer_lines() -> list[str]:
    return [
        'flow "agent.answer": requires true',
        '  let incoming_context is ""',
        "  try:",
        "    let provided_context is input.context",
        "    set incoming_context is provided_context",
        "  with catch err:",
        "    set incoming_context is incoming_context",
        '  let route_result is call flow "agent.route":',
        "    input:",
        "      message is input.message",
        "      context is incoming_context",
        "    output:",
        "      route",
        "      query",
        "      context",
        '  let route_query is map get route_result key "query"',
        '  let route_context is map get route_result key "context"',
        '  let retrieve_result is call flow "agent.retrieve":',
        "    input:",
        "      query is route_query",
        "      context is route_context",
        "    output:",
        "      context",
        "      citations",
        '  let retrieved_context is map get retrieve_result key "context"',
        '  let retrieved_citations is map get retrieve_result key "citations"',
        '  let policy_result is call flow "agent.tool_policy":',
        "    input:",
        '      tool_name is "agent.answer"',
        "    output:",
        "      allowed",
        "      reason",
        '  let policy_allowed is map get policy_result key "allowed"',
        "  if policy_allowed is false:",
        '    let fallback_result is call flow "agent.fallback":',
        "      input:",
        "        message is input.message",
        "        context is retrieved_context",
        '        error_text is "policy denied"',
        "      output:",
        "        answer_text",
        "        citations",
        "    return map:",
        '      "answer_text" is map get fallback_result key "answer_text"',
        '      "citations" is map get fallback_result key "citations"',
        '  if retrieved_context is "":',
        '    let fallback_result is call flow "agent.fallback":',
        "      input:",
        "        message is input.message",
        "        context is retrieved_context",
        '        error_text is "empty context"',
        "      output:",
        "        answer_text",
        "        citations",
        "    return map:",
        '      "answer_text" is map get fallback_result key "answer_text"',
        '      "citations" is map get fallback_result key "citations"',
        '  let generated_answer is ""',
        "  try:",
        f'    ask ai "{AGENT_WORKSPACE_INTERNAL_AI_NAME}" with structured input from map:',
        '      "query" is route_query',
        '      "context" is retrieved_context',
        "    as model_answer",
        '    if model_answer is "":',
        '      let fallback_result is call flow "agent.fallback":',
        "        input:",
        "          message is input.message",
        "          context is retrieved_context",
        '          error_text is "empty model output"',
        "        output:",
        "          answer_text",
        "          citations",
        '      set generated_answer is map get fallback_result key "answer_text"',
        "    else:",
        "      set generated_answer is model_answer",
        "  with catch err:",
        '    let fallback_result is call flow "agent.fallback":',
        "      input:",
        "        message is input.message",
        "        context is retrieved_context",
        '        error_text is "provider error"',
        "      output:",
        "        answer_text",
        "        citations",
        '    set generated_answer is map get fallback_result key "answer_text"',
        '  let formatted_citations is call flow "agent.citations.format":',
        "    input:",
        "      citations is retrieved_citations",
        "    output:",
        "      citations",
        "  return map:",
        '    "answer_text" is generated_answer',
        '    "citations" is map get formatted_citations key "citations"',
        "",
    ]


def _indent_lines(lines: list[str], *, prefix: str = "  ") -> list[str]:
    return [(prefix + line) if line else "" for line in lines]


def _escape_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\r", "\\r").replace("\n", "\\n")


__all__ = [
    "AgentWorkspacePresetConfig",
    "render_agent_workspace_source",
    "SUPPORTED_AGENT_WORKSPACE_PATTERNS",
    "SUPPORTED_AGENT_WORKSPACE_OVERRIDE_FLOWS",
    "AGENT_WORKSPACE_PATTERN_SINGLE_AGENT",
    "AGENT_WORKSPACE_PATTERN_ROUTER_SPECIALISTS",
    "AGENT_WORKSPACE_PATTERN_PLANNER_EXECUTOR",
    "AGENT_WORKSPACE_PATTERN_RESEARCH_RAG",
    "DEFAULT_AGENT_WORKSPACE_MODEL",
    "DEFAULT_AGENT_WORKSPACE_TEMPERATURE",
    "DEFAULT_AGENT_WORKSPACE_SYSTEM_PROMPT",
]
