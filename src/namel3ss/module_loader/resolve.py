from __future__ import annotations

from typing import Dict, Iterable

from namel3ss.ast import nodes as ast
from namel3ss.module_loader.resolve_names import qualify, resolve_name
from namel3ss.module_loader.resolve_walk import resolve_flow_steps, resolve_page_item, resolve_statements
from namel3ss.module_loader.resolve_walk.expressions import resolve_expression
from namel3ss.module_loader.types import ModuleExports


def collect_definitions(programs: Iterable[ast.Program]) -> Dict[str, set[str]]:
    defs: Dict[str, set[str]] = {
        "record": set(),
        "flow": set(),
        "job": set(),
        "page": set(),
        "ai": set(),
        "agent": set(),
        "tool": set(),
        "function": set(),
        "ui_pack": set(),
        "pattern": set(),
    }
    for program in programs:
        defs["record"].update({rec.name for rec in program.records})
        defs["function"].update({func.name for func in getattr(program, "functions", [])})
        defs["flow"].update({flow.name for flow in program.flows})
        defs["job"].update({job.name for job in getattr(program, "jobs", [])})
        defs["page"].update({page.name for page in program.pages})
        defs["ui_pack"].update({pack.name for pack in getattr(program, "ui_packs", [])})
        defs["pattern"].update({pattern.name for pattern in getattr(program, "ui_patterns", [])})
        defs["ai"].update({ai.name for ai in program.ais})
        defs["agent"].update({agent.name for agent in program.agents})
        defs["tool"].update({tool.name for tool in program.tools})
    return defs


def resolve_program(
    program: ast.Program,
    *,
    module_name: str | None,
    alias_map: Dict[str, str],
    local_defs: Dict[str, set[str]],
    exports_map: Dict[str, ModuleExports],
    context_label: str,
) -> None:
    for record in program.records:
        record.name = qualify(module_name, record.name)
    for crud in getattr(program, "crud", []) or []:
        crud.record_name = qualify(module_name, crud.record_name)
    for func in getattr(program, "functions", []):
        func.name = qualify(module_name, func.name)
        resolve_statements(
            func.body,
            module_name=module_name,
            alias_map=alias_map,
            local_defs=local_defs,
            exports_map=exports_map,
            context_label=context_label,
        )
    for flow in program.flows:
        flow.name = qualify(module_name, flow.name)
        resolve_statements(
            flow.body,
            module_name=module_name,
            alias_map=alias_map,
            local_defs=local_defs,
            exports_map=exports_map,
            context_label=context_label,
        )
        if getattr(flow, "steps", None):
            resolve_flow_steps(
                flow.steps,
                module_name=module_name,
                alias_map=alias_map,
                local_defs=local_defs,
                exports_map=exports_map,
                context_label=context_label,
            )
    for job in getattr(program, "jobs", []):
        job.name = qualify(module_name, job.name)
        resolve_statements(
            job.body,
            module_name=module_name,
            alias_map=alias_map,
            local_defs=local_defs,
            exports_map=exports_map,
            context_label=context_label,
        )
        if job.when is not None:
            resolve_expression(
                job.when,
                module_name=module_name,
                alias_map=alias_map,
                local_defs=local_defs,
                exports_map=exports_map,
                context_label=context_label,
            )
    for page in program.pages:
        page.name = qualify(module_name, page.name)
        for item in page.items:
            resolve_page_item(
                item,
                module_name=module_name,
                alias_map=alias_map,
                local_defs=local_defs,
                exports_map=exports_map,
                context_label=context_label,
            )
    for pack in getattr(program, "ui_packs", []):
        pack.name = qualify(module_name, pack.name)
        for fragment in pack.fragments:
            for item in fragment.items:
                resolve_page_item(
                    item,
                    module_name=module_name,
                    alias_map=alias_map,
                    local_defs=local_defs,
                    exports_map=exports_map,
                    context_label=context_label,
                )
    for pattern in getattr(program, "ui_patterns", []):
        pattern.name = qualify(module_name, pattern.name)
        for item in pattern.items:
            resolve_page_item(
                item,
                module_name=module_name,
                alias_map=alias_map,
                local_defs=local_defs,
                exports_map=exports_map,
                context_label=context_label,
            )
    for ai_flow in getattr(program, "ai_flows", []) or []:
        ai_flow.name = qualify(module_name, ai_flow.name)
        if ai_flow.return_expr is not None:
            resolve_expression(
                ai_flow.return_expr,
                module_name=module_name,
                alias_map=alias_map,
                local_defs=local_defs,
                exports_map=exports_map,
                context_label=context_label,
            )
        if ai_flow.output_type:
            ai_flow.output_type = _resolve_route_type(
                ai_flow.output_type,
                module_name=module_name,
                alias_map=alias_map,
                local_defs=local_defs,
                exports_map=exports_map,
                context_label=context_label,
                line=ai_flow.line,
                column=ai_flow.column,
            )
    for ai in program.ais:
        ai.name = qualify(module_name, ai.name)
        ai.exposed_tools = [
            resolve_name(
                tool_name,
                kind="tool",
                module_name=module_name,
                alias_map=alias_map,
                local_defs=local_defs,
                exports_map=exports_map,
                context_label=context_label,
                line=ai.line,
                column=ai.column,
            )
            for tool_name in ai.exposed_tools
        ]
    for agent in program.agents:
        agent.name = qualify(module_name, agent.name)
        agent.ai_name = resolve_name(
            agent.ai_name,
            kind="ai",
            module_name=module_name,
            alias_map=alias_map,
            local_defs=local_defs,
            exports_map=exports_map,
            context_label=context_label,
            line=agent.line,
            column=agent.column,
        )
    team = getattr(program, "agent_team", None)
    if team is not None:
        for member in team.members:
            member.name = resolve_name(
                member.name,
                kind="agent",
                module_name=module_name,
                alias_map=alias_map,
                local_defs=local_defs,
                exports_map=exports_map,
                context_label=context_label,
                line=member.line,
                column=member.column,
            )
    for tool in program.tools:
        tool.name = qualify(module_name, tool.name)

    for route in getattr(program, "routes", []) or []:
        route.name = qualify(module_name, route.name)
        route.flow_name = resolve_name(
            route.flow_name,
            kind="flow",
            module_name=module_name,
            alias_map=alias_map,
            local_defs=local_defs,
            exports_map=exports_map,
            context_label=context_label,
            line=route.line,
            column=route.column,
        )
        _resolve_route_fields(
            route,
            module_name=module_name,
            alias_map=alias_map,
            local_defs=local_defs,
            exports_map=exports_map,
            context_label=context_label,
        )


def _resolve_route_fields(
    route: ast.RouteDefinition,
    *,
    module_name: str | None,
    alias_map: Dict[str, str],
    local_defs: Dict[str, set[str]],
    exports_map: Dict[str, ModuleExports],
    context_label: str,
) -> None:
    for field_map in (route.parameters or {}, route.request or {}, route.response or {}):
        for field in field_map.values():
            field.type_name = _resolve_route_type(
                field.type_name,
                module_name=module_name,
                alias_map=alias_map,
                local_defs=local_defs,
                exports_map=exports_map,
                context_label=context_label,
                line=field.type_line or field.line,
                column=field.type_column or field.column,
            )


def _resolve_route_type(
    type_name: str,
    *,
    module_name: str | None,
    alias_map: Dict[str, str],
    local_defs: Dict[str, set[str]],
    exports_map: Dict[str, ModuleExports],
    context_label: str,
    line: int | None = None,
    column: int | None = None,
) -> str:
    if not isinstance(type_name, str) or not type_name:
        return type_name
    inner = _split_list_type(type_name)
    if inner is not None:
        resolved_inner = _resolve_route_type(
            inner,
            module_name=module_name,
            alias_map=alias_map,
            local_defs=local_defs,
            exports_map=exports_map,
            context_label=context_label,
            line=line,
            column=column,
        )
        return f"list<{resolved_inner}>"
    if type_name in {"text", "number", "boolean", "json"}:
        return type_name
    return resolve_name(
        type_name,
        kind="record",
        module_name=module_name,
        alias_map=alias_map,
        local_defs=local_defs,
        exports_map=exports_map,
        context_label=context_label,
        line=line,
        column=column,
    )


def _split_list_type(type_name: str) -> str | None:
    if not type_name.startswith("list<"):
        return None
    depth = 0
    start = None
    end = None
    for idx, ch in enumerate(type_name):
        if ch == "<":
            depth += 1
            if depth == 1:
                start = idx + 1
        elif ch == ">":
            depth -= 1
            if depth == 0:
                end = idx
                break
    if start is None or end is None or end != len(type_name) - 1:
        return None
    inner = type_name[start:end].strip()
    if not inner:
        return None
    return inner


__all__ = ["collect_definitions", "qualify", "resolve_program"]
