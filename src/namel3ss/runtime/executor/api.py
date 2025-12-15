from __future__ import annotations

from typing import Dict, Optional

from namel3ss.errors.base import Namel3ssError
from namel3ss.ir import nodes as ir
from namel3ss.runtime.ai.provider import AIProvider
from namel3ss.runtime.executor.executor import Executor
from namel3ss.runtime.executor.result import ExecutionResult
from namel3ss.runtime.store.memory_store import MemoryStore
from namel3ss.schema.records import RecordSchema


def execute_flow(
    flow: ir.Flow,
    schemas: Optional[Dict[str, RecordSchema]] = None,
    initial_state: Optional[Dict[str, object]] = None,
    input_data: Optional[Dict[str, object]] = None,
    ai_provider: Optional[AIProvider] = None,
    ai_profiles: Optional[Dict[str, ir.AIDecl]] = None,
) -> ExecutionResult:
    return Executor(
        flow,
        schemas=schemas,
        initial_state=initial_state,
        input_data=input_data,
        ai_provider=ai_provider,
        ai_profiles=ai_profiles,
    ).run()


def execute_program_flow(
    program: ir.Program,
    flow_name: str,
    *,
    state: Optional[Dict[str, object]] = None,
    input: Optional[Dict[str, object]] = None,
    store: Optional[MemoryStore] = None,
    ai_provider: Optional[AIProvider] = None,
) -> ExecutionResult:
    flow = next((f for f in program.flows if f.name == flow_name), None)
    if flow is None:
        raise Namel3ssError(f"Unknown flow '{flow_name}'")
    schemas = {schema.name: schema for schema in program.records}
    return Executor(
        flow,
        schemas=schemas,
        initial_state=state,
        input_data=input,
        store=store,
        ai_provider=ai_provider,
        ai_profiles=program.ais,
        agents=program.agents,
    ).run()
