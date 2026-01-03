from __future__ import annotations

from typing import Dict, Optional
import copy
from pathlib import Path

from namel3ss.config.loader import load_config
from namel3ss.config.model import AppConfig
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.ir import nodes as ir
from namel3ss.runtime.ai.provider import AIProvider
from namel3ss.runtime.executor.executor import Executor
from namel3ss.runtime.executor.result import ExecutionResult
from namel3ss.runtime.memory.api import MemoryManager
from namel3ss.runtime.storage.base import Storage
from namel3ss.runtime.storage.factory import resolve_store
from namel3ss.schema.records import RecordSchema
from namel3ss.runtime.theme.resolution import resolve_initial_theme
from namel3ss.observe import actor_summary, record_event, summarize_value
from namel3ss.secrets import collect_secret_values
from namel3ss.compatibility import validate_spec_version
import time


def execute_flow(
    flow: ir.Flow,
    schemas: Optional[Dict[str, RecordSchema]] = None,
    initial_state: Optional[Dict[str, object]] = None,
    input_data: Optional[Dict[str, object]] = None,
    ai_provider: Optional[AIProvider] = None,
    ai_profiles: Optional[Dict[str, ir.AIDecl]] = None,
    tools: Optional[Dict[str, ir.ToolDecl]] = None,
    functions: Optional[Dict[str, ir.FunctionDecl]] = None,
    identity: Optional[Dict[str, object]] = None,
) -> ExecutionResult:
    return Executor(
        flow,
        schemas=schemas,
        initial_state=initial_state,
        input_data=input_data,
        ai_provider=ai_provider,
        ai_profiles=ai_profiles,
        tools=tools,
        functions=functions,
        store=resolve_store(None),
        project_root=None,
        identity=identity,
    ).run()


def execute_program_flow(
    program: ir.Program,
    flow_name: str,
    *,
    state: Optional[Dict[str, object]] = None,
    input: Optional[Dict[str, object]] = None,
    store: Optional[Storage] = None,
    ai_provider: Optional[AIProvider] = None,
    memory_manager: Optional["MemoryManager"] = None,
    runtime_theme: Optional[str] = None,
    preference_store=None,
    preference_key: str | None = None,
    config: AppConfig | None = None,
    identity: dict | None = None,
) -> ExecutionResult:
    validate_spec_version(program)
    flow = next((f for f in program.flows if f.name == flow_name), None)
    if flow is None:
        raise Namel3ssError(_unknown_flow_message(flow_name, program.flows))
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
    resolved_config = config or load_config(
        app_path=getattr(program, "app_path", None),
        root=getattr(program, "project_root", None),
    )
    project_root = getattr(program, "project_root", None)
    resolved_root = project_root if isinstance(project_root, (str, type(None))) else str(project_root)
    secret_values = collect_secret_values(resolved_config)
    start_time = time.time()
    executor = Executor(
        flow,
        schemas=schemas,
        initial_state=state,
        input_data=input,
        store=resolve_store(store, config=resolved_config),
        ai_provider=ai_provider,
        ai_profiles=program.ais,
        agents=program.agents,
        tools=program.tools,
        functions=program.functions,
        memory_manager=memory_manager,
        runtime_theme=resolution.setting_used.value,
        config=resolved_config,
        identity_schema=getattr(program, "identity", None),
        identity=identity,
        project_root=resolved_root,
        app_path=getattr(program, "app_path", None),
    )
    module_traces = getattr(program, "module_traces", None)
    if module_traces:
        executor.ctx.traces.extend(copy.deepcopy(module_traces))
    actor = actor_summary(executor.ctx.identity)
    status = "ok"
    result: ExecutionResult | None = None
    error: Exception | None = None
    try:
        result = executor.run()
    except Exception as err:
        status = "error"
        error = err
        if resolved_root:
            record_event(
                Path(resolved_root),
                {
                    "type": "engine_error",
                    "kind": err.__class__.__name__,
                    "message": str(err),
                    "flow_name": flow_name,
                    "actor": actor,
                    "time": time.time(),
                },
                secret_values=secret_values,
            )
    finally:
        if resolved_root:
            record_event(
                Path(resolved_root),
                {
                    "type": "flow_run",
                    "flow_name": flow_name,
                    "status": status,
                    "time_start": start_time,
                    "time_end": time.time(),
                    "actor": actor,
                    "input_summary": summarize_value(input or {}, secret_values=secret_values),
                    "output_summary": summarize_value(result.last_value if result else None, secret_values=secret_values),
                },
                secret_values=secret_values,
            )
    if error:
        raise error
    if allow_override and preference_store and preference_key and getattr(program, "theme_preference", {}).get("persist") == "file":
        if result.runtime_theme in {"light", "dark", "system"}:
            preference_store.save_theme(preference_key, result.runtime_theme)
    if warning:
        result.traces.append({"type": "theme_warning", "message": warning})
    result.theme_source = resolution.source.value
    if result.runtime_theme is None:
        result.runtime_theme = resolution.setting_used.value
    return result


def _unknown_flow_message(flow_name: str, flows: list[ir.Flow]) -> str:
    available = [f.name for f in flows]
    sample = ", ".join(available[:5]) if available else "none defined"
    if len(available) > 5:
        sample += ", …"
    why = f"The app defines flows: {sample}."
    if not available:
        why = "The app does not define any flows."
    example = f'n3 app.ai flow "{available[0]}"' if available else 'flow "demo": return "ok"'
    return build_guidance_message(
        what=f"Unknown flow '{flow_name}'.",
        why=why,
        fix="Call an existing flow or add it to your app.ai file.",
        example=example,
    )
