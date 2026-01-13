from __future__ import annotations

from typing import Dict, List

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.ir.lowering.agents import _lower_agents
from namel3ss.ir.lowering.ai import _lower_ai_decls
from namel3ss.ir.lowering.flow import lower_flow
from namel3ss.ir.functions.lowering import lower_functions
from namel3ss.ir.lowering.identity import _lower_identity
from namel3ss.ir.lowering.pages import _lower_page
from namel3ss.ir.lowering.records import _lower_record
from namel3ss.ir.lowering.tools import _lower_tools
from namel3ss.ir.lowering.ui_packs import build_pack_index
from namel3ss.ir.model.agents import RunAgentsParallelStmt
from namel3ss.ir.model.program import Flow, Program
from namel3ss.ir.model.statements import ThemeChange, If, Repeat, RepeatWhile, ForEach, Match, MatchCase, TryCatch, ParallelBlock
from namel3ss.schema import records as schema


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
    agent_map = _lower_agents(program.agents, ai_map)
    function_map = lower_functions(program.functions, agent_map)
    flow_irs: List[Flow] = [lower_flow(flow, agent_map) for flow in program.flows]
    record_map: Dict[str, schema.RecordSchema] = {rec.name: rec for rec in record_schemas}
    flow_names = {flow.name for flow in flow_irs}
    pack_index = build_pack_index(getattr(program, "ui_packs", []))
    pages = [_lower_page(page, record_map, flow_names, pack_index) for page in program.pages]
    theme_runtime_supported = any(_flow_has_theme_change(flow) for flow in flow_irs)
    return Program(
        spec_version=str(program.spec_version),
        theme=program.app_theme,
        theme_tokens={name: val for name, (val, _, _) in program.theme_tokens.items()},
        theme_runtime_supported=theme_runtime_supported,
        theme_preference={
            "allow_override": program.theme_preference.get("allow_override", (False, None, None))[0],
            "persist": program.theme_preference.get("persist", ("none", None, None))[0],
        },
        records=record_schemas,
        functions=function_map,
        flows=flow_irs,
        pages=pages,
        ais=ai_map,
        tools=tool_map,
        agents=agent_map,
        identity=identity_schema,
        state_defaults=getattr(program, "state_defaults", None),
        line=program.line,
        column=program.column,
    )
