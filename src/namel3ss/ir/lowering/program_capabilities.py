from __future__ import annotations

from typing import Dict

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.ir.functions.model import FunctionDecl
from namel3ss.ir.model.agents import RunAgentStmt, RunAgentsParallelStmt
from namel3ss.ir.model.ai import AskAIStmt
from namel3ss.ir.model.program import Flow
from namel3ss.ir.model.statements import ForEach, If, Match, ParallelBlock, Repeat, RepeatWhile, TryCatch
from namel3ss.runtime.providers.capabilities import get_provider_capabilities
from namel3ss.runtime.providers.pack_registry import capability_for_provider, model_supports_mode


def require_program_capabilities(
    allowed: tuple[str, ...],
    tools: Dict[str, object],
    jobs: list[object],
    flows: list[Flow],
    functions: Dict[str, FunctionDecl],
    ais: Dict[str, object],
    agents: Dict[str, object],
) -> None:
    required: set[str] = set()
    for tool in tools.values():
        kind = getattr(tool, "kind", None)
        if kind == "http":
            required.add("http")
        elif kind == "file":
            required.add("files")
    if jobs:
        required.add("jobs")
    _collect_multimodal_requirements(
        required,
        flows=flows,
        jobs=jobs,
        functions=functions,
        ais=ais,
        agents=agents,
    )
    _collect_provider_requirements(required, ais=ais)
    missing = sorted(required - set(allowed))
    if not missing:
        return
    missing_text = ", ".join(missing)
    example_lines = ["capabilities:"]
    for capability in missing:
        example_lines.append(f"  {capability}")
    example = "\n".join(example_lines)
    raise Namel3ssError(
        build_guidance_message(
            what=f"Missing capabilities: {missing_text}.",
            why="Apps must explicitly enable built-in backend capabilities.",
            fix="Add a capabilities block that lists the missing entries.",
            example=example,
        )
    )


def _collect_multimodal_requirements(
    required: set[str],
    *,
    flows: list[Flow],
    jobs: list[object],
    functions: Dict[str, FunctionDecl],
    ais: Dict[str, object],
    agents: Dict[str, object],
) -> None:
    for flow in flows:
        _collect_multimodal_statement_requirements(
            flow.body,
            required=required,
            ais=ais,
            agents=agents,
        )
    for job in jobs:
        _collect_multimodal_statement_requirements(
            getattr(job, "body", []),
            required=required,
            ais=ais,
            agents=agents,
        )
    for function in functions.values():
        _collect_multimodal_statement_requirements(
            getattr(function, "body", []),
            required=required,
            ais=ais,
            agents=agents,
        )


def _collect_provider_requirements(required: set[str], *, ais: Dict[str, object]) -> None:
    for ai in ais.values():
        provider = str(getattr(ai, "provider", "") or "").strip().lower()
        capability = capability_for_provider(provider)
        if capability:
            required.add(capability)


def _collect_multimodal_statement_requirements(
    statements: list[object],
    *,
    required: set[str],
    ais: Dict[str, object],
    agents: Dict[str, object],
) -> None:
    for stmt in statements:
        if isinstance(stmt, AskAIStmt):
            _require_stream_support(
                stream=getattr(stmt, "stream", False),
                ai_name=stmt.ai_name,
                required=required,
                ais=ais,
                line=getattr(stmt, "line", None),
                column=getattr(stmt, "column", None),
            )
            _require_mode_support(
                mode=getattr(stmt, "input_mode", "text"),
                ai_name=stmt.ai_name,
                required=required,
                ais=ais,
                line=getattr(stmt, "line", None),
                column=getattr(stmt, "column", None),
            )
            continue
        if isinstance(stmt, RunAgentStmt):
            agent_decl = agents.get(stmt.agent_name)
            ai_name = getattr(agent_decl, "ai_name", None)
            if isinstance(ai_name, str) and ai_name:
                _require_mode_support(
                    mode=getattr(stmt, "input_mode", "text"),
                    ai_name=ai_name,
                    required=required,
                    ais=ais,
                    line=getattr(stmt, "line", None),
                    column=getattr(stmt, "column", None),
                )
            continue
        if isinstance(stmt, RunAgentsParallelStmt):
            for entry in getattr(stmt, "entries", []):
                agent_decl = agents.get(getattr(entry, "agent_name", ""))
                ai_name = getattr(agent_decl, "ai_name", None)
                if isinstance(ai_name, str) and ai_name:
                    _require_mode_support(
                        mode=getattr(entry, "input_mode", "text"),
                        ai_name=ai_name,
                        required=required,
                        ais=ais,
                        line=getattr(entry, "line", None),
                        column=getattr(entry, "column", None),
                    )
            continue
        if isinstance(stmt, If):
            _collect_multimodal_statement_requirements(
                stmt.then_body,
                required=required,
                ais=ais,
                agents=agents,
            )
            _collect_multimodal_statement_requirements(
                stmt.else_body,
                required=required,
                ais=ais,
                agents=agents,
            )
            continue
        if isinstance(stmt, Repeat):
            _collect_multimodal_statement_requirements(
                stmt.body,
                required=required,
                ais=ais,
                agents=agents,
            )
            continue
        if isinstance(stmt, RepeatWhile):
            _collect_multimodal_statement_requirements(
                stmt.body,
                required=required,
                ais=ais,
                agents=agents,
            )
            continue
        if isinstance(stmt, ForEach):
            _collect_multimodal_statement_requirements(
                stmt.body,
                required=required,
                ais=ais,
                agents=agents,
            )
            continue
        if isinstance(stmt, Match):
            for case in stmt.cases:
                _collect_multimodal_statement_requirements(
                    case.body,
                    required=required,
                    ais=ais,
                    agents=agents,
                )
            if stmt.otherwise:
                _collect_multimodal_statement_requirements(
                    stmt.otherwise,
                    required=required,
                    ais=ais,
                    agents=agents,
                )
            continue
        if isinstance(stmt, TryCatch):
            _collect_multimodal_statement_requirements(
                stmt.try_body,
                required=required,
                ais=ais,
                agents=agents,
            )
            _collect_multimodal_statement_requirements(
                stmt.catch_body,
                required=required,
                ais=ais,
                agents=agents,
            )
            continue
        if isinstance(stmt, ParallelBlock):
            for task in stmt.tasks:
                _collect_multimodal_statement_requirements(
                    task.body,
                    required=required,
                    ais=ais,
                    agents=agents,
                )


def _require_stream_support(
    *,
    stream: object,
    ai_name: str,
    required: set[str],
    ais: Dict[str, object],
    line: int | None,
    column: int | None,
) -> None:
    if not bool(stream):
        return
    required.add("streaming")
    ai_decl = ais.get(ai_name)
    if ai_decl is None:
        return
    provider = str(getattr(ai_decl, "provider", "")).lower()
    model = str(getattr(ai_decl, "model", ""))
    provider_capabilities = get_provider_capabilities(provider)
    if provider_capabilities.supports_streaming:
        return
    raise Namel3ssError(
        build_guidance_message(
            what=f'AI "{ai_name}" model "{model}" does not support stream=true.',
            why=f'Provider "{provider}" is configured without streaming support.',
            fix="Use a provider/model with streaming support or remove stream=true.",
            example='ask ai "assistant" with stream: false and input: "hello" as reply',
        ),
        line=line,
        column=column,
    )


def _require_mode_support(
    *,
    mode: object,
    ai_name: str,
    required: set[str],
    ais: Dict[str, object],
    line: int | None,
    column: int | None,
) -> None:
    value = str(mode or "text").strip().lower()
    if value in {"text", "structured"}:
        return
    ai_decl = ais.get(ai_name)
    if ai_decl is None:
        return
    provider = str(getattr(ai_decl, "provider", "")).lower()
    model = str(getattr(ai_decl, "model", ""))
    provider_capabilities = get_provider_capabilities(provider)
    if not model_supports_mode(model_identifier=model, mode=value):
        raise Namel3ssError(
            build_guidance_message(
                what=f'AI "{ai_name}" model "{model}" does not support {value} mode.',
                why="The selected provider pack does not support this mode for the model.",
                fix="Choose a compatible model for this mode.",
                example=f'model is "{model.split(":", 1)[0]}:{_mode_example(value)}"',
            ),
            line=line,
            column=column,
        )
    if value == "image":
        required.add("vision")
        if provider_capabilities.supports_vision:
            return
        raise Namel3ssError(
            build_guidance_message(
                what=f'AI "{ai_name}" model "{model}" does not support image input mode.',
                why=f'Provider "{provider}" is configured without vision support.',
                fix='Use a provider/model with vision support or switch to `with input:`.',
                example='capabilities:\n  vision',
            ),
            line=line,
            column=column,
        )
    if value == "audio":
        required.add("speech")
        if provider_capabilities.supports_audio:
            return
        raise Namel3ssError(
            build_guidance_message(
                what=f'AI "{ai_name}" model "{model}" does not support audio input mode.',
                why=f'Provider "{provider}" is configured without speech support.',
                fix='Use a provider/model with speech support or switch to `with input:`.',
                example='capabilities:\n  speech',
            ),
            line=line,
            column=column,
        )
    raise Namel3ssError(
        f"Unknown AI input mode '{value}'.",
        line=line,
        column=column,
    )


def _mode_example(mode: str) -> str:
    token = str(mode or "text").strip().lower()
    if token == "image":
        return "stable-diffusion"
    if token == "audio":
        return "whisper-base"
    return "model"


__all__ = ["require_program_capabilities"]
