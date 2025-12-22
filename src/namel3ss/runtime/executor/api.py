from __future__ import annotations

from typing import Dict, Optional

from namel3ss.errors.base import Namel3ssError
from namel3ss.ir import nodes as ir
from namel3ss.runtime.ai.provider import AIProvider
from namel3ss.runtime.executor.executor import Executor
from namel3ss.runtime.executor.result import ExecutionResult
from namel3ss.runtime.storage.base import Storage
from namel3ss.runtime.storage.factory import resolve_store
from namel3ss.schema.records import RecordSchema
from namel3ss.runtime.theme.resolution import resolve_initial_theme


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
        store=resolve_store(None),
    ).run()


def execute_program_flow(
    program: ir.Program,
    flow_name: str,
    *,
    state: Optional[Dict[str, object]] = None,
    input: Optional[Dict[str, object]] = None,
    store: Optional[Storage] = None,
    ai_provider: Optional[AIProvider] = None,
    runtime_theme: Optional[str] = None,
    preference_store=None,
    preference_key: str | None = None,
) -> ExecutionResult:
    flow = next((f for f in program.flows if f.name == flow_name), None)
    if flow is None:
        raise Namel3ssError(f"Unknown flow '{flow_name}'")
    schemas = {schema.name: schema for schema in program.records}
    pref_policy = getattr(program, "theme_preference", {}) or {}
    allow_override = pref_policy.get("allow_override", False)
    persist_mode = pref_policy.get("persist", "none")
    persisted, warning = (None, None)
    if allow_override and persist_mode == "file" and preference_store and preference_key:
        persisted, warning = preference_store.load_theme(preference_key)
    resolution = resolve_initial_theme(
        allow_override=allow_override,
        persist_mode=persist_mode,
        persisted_value=persisted,
        session_theme=runtime_theme,
        app_setting=getattr(program, "theme", "system"),
        system_available=False,
        system_value=None,
    )
    result = Executor(
        flow,
        schemas=schemas,
        initial_state=state,
        input_data=input,
        store=resolve_store(store),
        ai_provider=ai_provider,
        ai_profiles=program.ais,
        agents=program.agents,
        runtime_theme=resolution.setting_used.value,
    ).run()
    if allow_override and preference_store and preference_key and getattr(program, "theme_preference", {}).get("persist") == "file":
        if result.runtime_theme in {"light", "dark", "system"}:
            preference_store.save_theme(preference_key, result.runtime_theme)
    if warning:
        result.traces.append({"type": "theme_warning", "message": warning})
    result.theme_source = resolution.source.value
    if result.runtime_theme is None:
        result.runtime_theme = resolution.setting_used.value
    return result
