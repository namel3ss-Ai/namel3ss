from __future__ import annotations

from typing import Dict, List

from namel3ss.ast import nodes as ast
from namel3ss.ir.lowering.agents import _lower_agents
from namel3ss.ir.lowering.ai import _lower_ai_decls
from namel3ss.ir.lowering.flow import lower_flow
from namel3ss.ir.lowering.pages import _lower_page
from namel3ss.ir.lowering.records import _lower_record
from namel3ss.ir.lowering.tools import _lower_tools
from namel3ss.ir.model.program import Flow, Program
from namel3ss.schema import records as schema


def lower_program(program: ast.Program) -> Program:
    record_schemas = [_lower_record(record) for record in program.records]
    tool_map = _lower_tools(program.tools)
    ai_map = _lower_ai_decls(program.ais, tool_map)
    agent_map = _lower_agents(program.agents, ai_map)
    flow_irs: List[Flow] = [lower_flow(flow, agent_map) for flow in program.flows]
    record_map: Dict[str, schema.RecordSchema] = {rec.name: rec for rec in record_schemas}
    flow_names = {flow.name for flow in flow_irs}
    pages = [_lower_page(page, record_map, flow_names) for page in program.pages]
    return Program(
        records=record_schemas,
        flows=flow_irs,
        pages=pages,
        ais=ai_map,
        tools=tool_map,
        agents=agent_map,
        line=program.line,
        column=program.column,
    )
