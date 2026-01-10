from __future__ import annotations

from pathlib import Path

from namel3ss.module_loader import load_project
from namel3ss.runtime.executor.executor import Executor
from namel3ss.runtime.memory.api import MemoryManager
from namel3ss.runtime.store.memory_store import MemoryStore


def _template_root() -> Path:
    return Path(__file__).resolve().parents[2] / "src" / "namel3ss" / "templates" / "agent_wow"


def test_agent_wow_generate_plan_does_not_write_missing_message() -> None:
    program = load_project(_template_root() / "app.ai").program
    flow = next(flow for flow in program.flows if flow.name == "agent_wow.generate_plan")
    schemas = {schema.name: schema for schema in program.records}
    store = MemoryStore()
    schema = schemas["agent_wow.ProjectBrief"]
    store.save(schema, {"description": "Launch plan"})
    executor = Executor(
        flow,
        schemas=schemas,
        store=store,
        ai_profiles=program.ais,
        agents=program.agents,
        tools=program.tools,
        functions=program.functions,
        memory_manager=MemoryManager(project_root=None, app_path=None),
        project_root=None,
        app_path=None,
    )
    result = executor.run()
    status = result.state.get("status") if isinstance(result.state, dict) else None
    message = status.get("message") if isinstance(status, dict) else None
    assert message != "Add a project description, then try again."
    assert result.last_value != "missing_project_brief"
