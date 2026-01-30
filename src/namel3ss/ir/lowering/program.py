from __future__ import annotations

from typing import Dict, List

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.ir.lowering.agents import _lower_agent_team, _lower_agents
from namel3ss.ir.lowering.ai import _lower_ai_decls
from namel3ss.ir.lowering.flow import lower_flow
from namel3ss.ir.lowering.contracts import lower_flow_contracts
from namel3ss.ir.lowering.jobs import lower_jobs
from namel3ss.ir.lowering.policy import lower_policy
from namel3ss.flow_contract import (
    validate_declarative_flows,
    validate_flow_names,
    validate_flow_contracts,
    validate_flow_composition,
    validate_flow_purity,
)
from namel3ss.ir.functions.lowering import lower_functions
from namel3ss.ir.lowering.identity import _lower_identity
from namel3ss.ir.lowering.pages import _lower_page
from namel3ss.ir.lowering.records import _lower_record
from namel3ss.ir.lowering.tools import _lower_tools
from namel3ss.ir.lowering.ui_packs import build_pack_index
from namel3ss.ir.lowering.ui_patterns import build_pattern_index
from namel3ss.ir.model.agents import RunAgentsParallelStmt
from namel3ss.ir.model.program import Flow, Program
from namel3ss.ir.model.pages import Page
from namel3ss.ir.model.statements import ThemeChange, If, Repeat, RepeatWhile, ForEach, Match, MatchCase, TryCatch, ParallelBlock
from namel3ss.schema import records as schema
from namel3ss.ui.settings import normalize_ui_settings
from namel3ss.validation import ValidationMode
from namel3ss.lang.capabilities import normalize_builtin_capability
from namel3ss.pipelines.registry import pipeline_contracts


def _statement_has_theme_change(stmt) -> bool:
    if isinstance(stmt, ThemeChange):
        return True
    if isinstance(stmt, If):
        return any(_statement_has_theme_change(s) for s in stmt.then_body) or any(_statement_has_theme_change(s) for s in stmt.else_body)
    if isinstance(stmt, Repeat):
        return any(_statement_has_theme_change(s) for s in stmt.body)
    if isinstance(stmt, RepeatWhile):
        return any(_statement_has_theme_change(s) for s in stmt.body)
    if isinstance(stmt, ForEach):
        return any(_statement_has_theme_change(s) for s in stmt.body)
    if isinstance(stmt, Match):
        return any(_statement_has_theme_change(c) for c in stmt.cases) or (any(_statement_has_theme_change(s) for s in stmt.otherwise) if stmt.otherwise else False)
    if isinstance(stmt, MatchCase):
        return any(_statement_has_theme_change(s) for s in stmt.body)
    if isinstance(stmt, TryCatch):
        return any(_statement_has_theme_change(s) for s in stmt.try_body) or any(_statement_has_theme_change(s) for s in stmt.catch_body)
    if isinstance(stmt, ParallelBlock):
        return any(_statement_has_theme_change(s) for task in stmt.tasks for s in task.body)
    if isinstance(stmt, RunAgentsParallelStmt):
        return any(_statement_has_theme_change(e) for e in stmt.entries)
    return False


def _flow_has_theme_change(flow: Flow) -> bool:
    return any(_statement_has_theme_change(stmt) for stmt in flow.body)


def lower_program(program: ast.Program) -> Program:
    if not getattr(program, "spec_version", None):
        raise Namel3ssError(
            build_guidance_message(
                what="Spec declaration is missing.",
                why="Programs must declare a spec version before lowering.",
                fix='Add a spec declaration at the top of the file.',
                example='spec is \"1.0\"',
            )
        )
    record_schemas = [_lower_record(record) for record in program.records]
    identity_schema = _lower_identity(program.identity) if program.identity else None
    tool_map = _lower_tools(program.tools)
    ai_map = _lower_ai_decls(program.ais, tool_map)
    agent_team = _lower_agent_team(getattr(program, "agent_team", None), program.agents)
    agent_map = _lower_agents(program.agents, ai_map, agent_team)
    function_map = lower_functions(program.functions, agent_map)
    flow_contracts = lower_flow_contracts(getattr(program, "contracts", []) or [])
    flow_irs: List[Flow] = [lower_flow(flow, agent_map) for flow in program.flows]
    job_irs = lower_jobs(getattr(program, "jobs", []), agent_map)
    record_map: Dict[str, schema.RecordSchema] = {rec.name: rec for rec in record_schemas}
    flow_names = validate_flow_names(flow_irs)
    validate_flow_contracts(flow_irs, flow_contracts)
    validate_flow_composition(flow_irs, flow_contracts, pipeline_contracts())
    validate_flow_purity(flow_irs, flow_contracts)
    validate_declarative_flows(flow_irs, record_map, tool_map, mode=ValidationMode.RUNTIME, warnings=None)
    capabilities = _normalize_capabilities(getattr(program, "capabilities", []) or [])
    _require_capabilities(capabilities, tool_map, job_irs)
    pack_allowlist = _normalize_pack_allowlist(getattr(program, "pack_allowlist", None))
    pack_index = build_pack_index(getattr(program, "ui_packs", []))
    pattern_index = build_pattern_index(getattr(program, "ui_patterns", []), pack_index)
    page_names = {page.name for page in program.pages}
    pages = [
        _lower_page(page, record_map, flow_names, page_names, pack_index, pattern_index)
        for page in program.pages
    ]
    _ensure_unique_pages(pages)
    theme_runtime_supported = any(_flow_has_theme_change(flow) for flow in flow_irs)
    ui_settings = normalize_ui_settings(getattr(program, "ui_settings", None))
    theme_setting = ui_settings.get("theme", program.app_theme)
    lowered = Program(
        spec_version=str(program.spec_version),
        theme=theme_setting,
        theme_tokens={name: val for name, (val, _, _) in program.theme_tokens.items()},
        theme_runtime_supported=theme_runtime_supported,
        theme_preference={
            "allow_override": program.theme_preference.get("allow_override", (False, None, None))[0],
            "persist": program.theme_preference.get("persist", ("none", None, None))[0],
        },
        ui_settings=ui_settings,
        capabilities=capabilities,
        records=record_schemas,
        functions=function_map,
        flow_contracts=flow_contracts,
        flows=flow_irs,
        jobs=job_irs,
        pages=pages,
        ais=ai_map,
        tools=tool_map,
        agents=agent_map,
        policy=lower_policy(getattr(program, "policy", None)),
        agent_team=agent_team,
        identity=identity_schema,
        state_defaults=getattr(program, "state_defaults", None),
        line=program.line,
        column=program.column,
    )
    setattr(lowered, "pack_allowlist", pack_allowlist)
    return lowered


def _ensure_unique_pages(pages: list[Page]) -> None:
    seen: dict[str, object] = {}
    for page in pages:
        if page.name in seen:
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Page '{page.name}' is declared more than once.",
                    why="Pages must have unique names.",
                    fix="Rename the duplicate page or merge its contents.",
                    example='page "home":',
                ),
                line=getattr(page, "line", None),
                column=getattr(page, "column", None),
            )
        seen[page.name] = True


def _normalize_capabilities(items: list[str]) -> tuple[str, ...]:
    normalized: list[str] = []
    for item in items:
        value = normalize_builtin_capability(item)
        if value:
            normalized.append(value)
    return tuple(sorted(set(normalized)))


def _normalize_pack_allowlist(items: list[str] | None) -> tuple[str, ...] | None:
    if items is None:
        return None
    normalized: list[str] = []
    seen: set[str] = set()
    for item in items:
        if not isinstance(item, str):
            continue
        value = item.strip()
        if not value or value in seen:
            continue
        seen.add(value)
        normalized.append(value)
    if not normalized:
        return None
    return tuple(normalized)


def _require_capabilities(
    allowed: tuple[str, ...],
    tools: Dict[str, object],
    jobs: list,
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
    missing = sorted(required - set(allowed))
    if not missing:
        return
    missing_text = ", ".join(missing)
    raise Namel3ssError(
        build_guidance_message(
            what=f"Missing capabilities: {missing_text}.",
            why="Apps must explicitly enable built-in backend capabilities.",
            fix="Add a capabilities block that lists the missing entries.",
            example="capabilities:\n  http\n  jobs\n  files",
        )
    )
