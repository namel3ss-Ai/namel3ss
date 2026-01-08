from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.format import format_source
from namel3ss.lint.engine import lint_source
from namel3ss.module_loader import load_project
from namel3ss.parser.core import parse
from namel3ss.studio.agent_builder.templates import (
    PATTERNS,
    memory_preset,
    render_agent_block,
    render_ai_block,
    render_pattern_flow,
    render_pattern_snippet,
)


@dataclass(frozen=True)
class WizardResult:
    app_path: Path
    updated_files: list[str]
    snippet: str


_AGENT_PROMPTS = {
    "router": {
        "billing": "Handle billing questions.",
        "sales": "Handle sales questions.",
        "support": "Handle support questions.",
    },
    "planner_executor": {
        "planner": "Draft a crisp plan with numbered steps.",
        "executor": "Execute the plan deterministically and summarize results.",
    },
    "reviewer_critic": {
        "drafter": "Draft a clear response in one pass.",
        "reviewer": "Critique the draft and return improvements.",
    },
    "parallel_coordinator": {
        "worker_one": "Provide a concise perspective on the task.",
        "worker_two": "Provide a concise alternative on the task.",
        "worker_three": "Provide a concise risk check on the task.",
    },
    "safe_action_tool_first": {
        "planner": "Propose a safe, reversible action only.",
    },
}

_AI_PROMPTS = {
    "router": "Route requests to the right specialist.",
    "planner_executor": "Produce plans that are safe to execute deterministically.",
    "reviewer_critic": "Provide grounded critique and concise edits.",
    "parallel_coordinator": "Provide focused, bounded responses for coordination.",
    "safe_action_tool_first": "Propose safe, reversible actions only.",
}


def apply_agent_wizard(source: str, app_path: str, payload: dict) -> dict:
    result = _apply_agent_wizard(source, app_path, payload)
    return {
        "ok": True,
        "updated_files": result.updated_files,
    }


def _apply_agent_wizard(source: str, app_path: str, payload: dict) -> WizardResult:
    app_file = Path(app_path)
    project = load_project(app_file, source_overrides={app_file: source})
    program = project.program
    pattern_id = _require_text(payload.get("pattern"), "pattern")
    if pattern_id not in PATTERNS:
        raise Namel3ssError(f"Unknown pattern '{pattern_id}'.")
    spec = PATTERNS[pattern_id]
    agents = _coerce_agent_roles(payload.get("agents"), spec.roles)
    _validate_agent_names(agents)
    _assert_new_names("agent", agents.values(), program.agents.keys())

    create_ai = bool(payload.get("create_ai", True))
    ai_name = _require_text(payload.get("ai_name"), "ai_name")
    if create_ai:
        _assert_new_names("AI", [ai_name], program.ais.keys())
    else:
        if ai_name not in program.ais:
            raise Namel3ssError(f"AI profile '{ai_name}' was not found.")

    flow_name = _unique_name(f"{pattern_id}_run", {flow.name for flow in program.flows})

    tool_name = None
    tool_fields: list[str] = []
    if spec.requires_tools:
        tool_name = _require_text(payload.get("tool_name"), "tool_name")
        if tool_name not in program.tools:
            raise Namel3ssError(f"Tool '{tool_name}' was not found.")
        tool_fields = [field.name for field in program.tools[tool_name].input_fields]

    ai_block = None
    if create_ai:
        provider = _optional_text(payload.get("ai_provider"), default="mock")
        model = _optional_text(payload.get("ai_model"), default="mock-model")
        tools = _filter_tools(payload.get("ai_tools"), program.tools.keys())
        memory_key = str(payload.get("ai_memory") or "minimal")
        preset = memory_preset(memory_key)
        ai_block = render_ai_block(
            name=ai_name,
            provider=provider,
            model=model,
            system_prompt=_AI_PROMPTS.get(pattern_id, ""),
            tools=tools,
            memory=preset,
        )

    agent_blocks = []
    for role in spec.roles:
        agent_blocks.append(
            render_agent_block(
                name=agents[role],
                ai_name=ai_name,
                system_prompt=_AGENT_PROMPTS[pattern_id][role],
            )
        )

    flow_lines = render_pattern_flow(
        pattern_id=pattern_id,
        flow_name=flow_name,
        roles=agents,
        tool_name=tool_name,
        tool_fields=tool_fields,
    )
    snippet = render_pattern_snippet(
        pattern_id=pattern_id,
        ai_block=ai_block,
        agent_blocks=agent_blocks,
        flow_lines=flow_lines,
    )
    snippet = format_source(snippet).strip() + "\n"

    updated_files: list[str] = []
    use_module = _should_use_module(source, snippet)
    if use_module:
        module_path, alias = _next_module_path(app_file, pattern_id, agents[spec.roles[0]], project.app_ast.uses)
        module_path.parent.mkdir(parents=True, exist_ok=True)
        module_path.write_text(snippet, encoding="utf-8")
        updated_files.append(module_path.as_posix())
        use_line = f'use module "{module_path.relative_to(app_file.parent).as_posix()}" as {alias}'
        new_source = _append_block(source, use_line)
        if len(new_source.splitlines()) > 500:
            raise Namel3ssError(
                build_guidance_message(
                    what="app.ai exceeds the 500 line limit after adding a module reference.",
                    why="Studio keeps files small to preserve single-responsibility.",
                    fix="Remove unused code or move more logic into modules.",
                    example='use module "modules/agent_patterns/router.ai" as router',
                )
            )
    else:
        new_source = _append_block(source, snippet.rstrip())

    _validate_app_source(new_source)
    app_file.write_text(new_source, encoding="utf-8")
    updated_files.append(app_file.as_posix())
    return WizardResult(app_path=app_file, updated_files=updated_files, snippet=snippet)


def _should_use_module(source: str, snippet: str) -> bool:
    lines = len(source.splitlines())
    added = len(snippet.splitlines())
    return (lines + added) > 500


def _append_block(source: str, block: str) -> str:
    trimmed = source.rstrip()
    return f"{trimmed}\n\n{block}\n"


def _validate_app_source(source: str) -> None:
    parse(source)
    findings = lint_source(source)
    errors = [finding for finding in findings if finding.severity == "error"]
    if errors:
        messages = "; ".join(finding.message for finding in errors)
        raise Namel3ssError(f"Generated code failed lint: {messages}")


def _next_module_path(app_file: Path, pattern_id: str, lead_name: str, uses) -> tuple[Path, str]:
    slug = _slugify(lead_name) or pattern_id
    alias = _unique_alias(f"{pattern_id}_{slug}", {use.alias for use in uses})
    base_dir = app_file.parent / "modules" / "agent_patterns"
    candidate = base_dir / f"{pattern_id}_{slug}.ai"
    if not candidate.exists():
        return candidate, alias
    index = 2
    while True:
        candidate = base_dir / f"{pattern_id}_{slug}_{index}.ai"
        if not candidate.exists():
            return candidate, f"{alias}_{index}"
        index += 1


def _unique_alias(base: str, existing: Iterable[str]) -> str:
    if base not in existing:
        return base
    index = 2
    while f"{base}_{index}" in existing:
        index += 1
    return f"{base}_{index}"


def _unique_name(base: str, existing: set[str]) -> str:
    if base not in existing:
        return base
    index = 2
    while f"{base}_{index}" in existing:
        index += 1
    return f"{base}_{index}"


def _coerce_agent_roles(raw: object, roles: Iterable[str]) -> dict[str, str]:
    if isinstance(raw, dict):
        data = {str(key): str(value) for key, value in raw.items()}
    elif isinstance(raw, list):
        data = {str(item.get("role")): str(item.get("name")) for item in raw if isinstance(item, dict)}
    else:
        data = {}
    normalized: dict[str, str] = {}
    for role in roles:
        value = data.get(role, "")
        if not value:
            raise Namel3ssError(_missing_role_message(role))
        normalized[role] = value
    return normalized


def _missing_role_message(role: str) -> str:
    return build_guidance_message(
        what=f"Missing agent name for {role}.",
        why="Each pattern role must be named explicitly.",
        fix="Provide a name for every agent role.",
        example=f"{role}_agent",
    )


def _validate_agent_names(agents: dict[str, str]) -> None:
    seen = set()
    for role, name in agents.items():
        if not name or not name.strip():
            raise Namel3ssError(_missing_role_message(role))
        if name in seen:
            raise Namel3ssError(f"Duplicate agent name '{name}'.")
        seen.add(name)


def _assert_new_names(label: str, names: Iterable[str], existing: Iterable[str]) -> None:
    existing_set = set(existing)
    for name in names:
        if name in existing_set:
            raise Namel3ssError(f"{label} '{name}' already exists.")


def _filter_tools(raw: object, available: Iterable[str]) -> list[str]:
    if not raw:
        return []
    if not isinstance(raw, list):
        raise Namel3ssError("Tool list must be an array.")
    available_set = set(available)
    selected: list[str] = []
    for entry in raw:
        if not entry:
            continue
        name = str(entry)
        if name not in available_set:
            raise Namel3ssError(f"Tool '{name}' was not found.")
        selected.append(name)
    return sorted(set(selected))


def _require_text(value: object, label: str) -> str:
    if value is None:
        raise Namel3ssError(f"{label} is required.")
    text = str(value).strip()
    if not text:
        raise Namel3ssError(f"{label} is required.")
    return text


def _optional_text(value: object, *, default: str) -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text or default


def _slugify(value: str) -> str:
    text = "".join(ch.lower() if ch.isalnum() else "_" for ch in value)
    text = "_".join(part for part in text.split("_") if part)
    if not text:
        return ""
    if text[0].isdigit():
        text = f"agent_{text}"
    return text


__all__ = ["apply_agent_wizard"]
