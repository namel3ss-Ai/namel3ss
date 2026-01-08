from __future__ import annotations

from typing import Dict, Iterable

from namel3ss.ast import nodes as ast
from namel3ss.module_loader.resolve_names import qualify, resolve_name
from namel3ss.module_loader.resolve_walk import resolve_page_item, resolve_statements
from namel3ss.module_loader.types import ModuleExports


def collect_definitions(programs: Iterable[ast.Program]) -> Dict[str, set[str]]:
    defs: Dict[str, set[str]] = {
        "record": set(),
        "flow": set(),
        "page": set(),
        "ai": set(),
        "agent": set(),
        "tool": set(),
        "function": set(),
        "ui_pack": set(),
    }
    for program in programs:
        defs["record"].update({rec.name for rec in program.records})
        defs["function"].update({func.name for func in getattr(program, "functions", [])})
        defs["flow"].update({flow.name for flow in program.flows})
        defs["page"].update({page.name for page in program.pages})
        defs["ui_pack"].update({pack.name for pack in getattr(program, "ui_packs", [])})
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
    for tool in program.tools:
        tool.name = qualify(module_name, tool.name)


__all__ = ["collect_definitions", "qualify", "resolve_program"]
