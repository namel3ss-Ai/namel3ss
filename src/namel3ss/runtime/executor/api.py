from __future__ import annotations

from typing import Dict, Optional
import copy
from pathlib import Path

from namel3ss.config.loader import load_config
from namel3ss.config.model import AppConfig
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.auth.enforcement import enforce_requirement
from namel3ss.ir import nodes as ir
from namel3ss.runtime.ai.provider import AIProvider
from namel3ss.runtime.auth.route_permissions import load_route_permissions
from namel3ss.runtime.executor.executor import Executor
from namel3ss.runtime.executor.native_exec import NativeExecConfig, try_native_execute
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
from namel3ss.governance.policy import enforce_policies_for_app, enforce_runtime_request_policies
from namel3ss.observability.context import ObservabilityContext
from namel3ss.observability.enablement import resolve_observability_context
from namel3ss.pipelines.registry import pipeline_contracts
from namel3ss.runtime.performance.config import normalize_performance_runtime_config
from namel3ss.runtime.performance.guard import require_performance_capability


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
    auth_context: object | None = None,
    session: dict | None = None,
    observability: ObservabilityContext | None = None,
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
        pipeline_contracts=pipeline_contracts(),
        store=resolve_store(None),
        project_root=None,
        identity=identity,
        auth_context=auth_context,
        session=session,
        observability=observability,
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
    auth_context: object | None = None,
    session: dict | None = None,
    action_id: str | None = None,
    route_name: str | None = None,
    observability: ObservabilityContext | None = None,
) -> ExecutionResult:
    validate_spec_version(program)
    project_root = getattr(program, "project_root", None)
    app_path_value = getattr(program, "app_path", None)
    enforce_policies_for_app(project_root=project_root, app_path=app_path_value)
    flow = next((f for f in program.flows if f.name == flow_name), None)
    if flow is None:
        raise Namel3ssError(_unknown_flow_message(flow_name, program.flows))
    permissions = load_route_permissions(project_root, app_path_value)
    enforce_requirement(
        permissions.flow_requirement_for(flow_name),
        resource_name=f"flow:{flow_name}",
        identity=identity,
        auth_context=auth_context,
    )
    enforce_runtime_request_policies(
        project_root=project_root,
        app_path=app_path_value,
        route_name=route_name or "",
        flow_name=flow_name,
        payload=input or {},
    )
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
    require_performance_capability(
        getattr(program, "capabilities", ()),
        normalize_performance_runtime_config(resolved_config),
        where="runtime configuration",
    )
    resolved_root = project_root if isinstance(project_root, (str, type(None))) else str(project_root)
    app_path = app_path_value
    if resolved_root is None and app_path is None:
        native_config = NativeExecConfig(
            flow_name=flow_name,
            runtime_theme=resolution.setting_used.value,
            theme_source=resolution.source.value,
        )
        native_result = try_native_execute(program, flow, native_config)
        if native_result is not None:
            if native_result.runtime_theme is None:
                native_result.runtime_theme = resolution.setting_used.value
            native_result.theme_source = resolution.source.value
            return native_result
    secret_values = collect_secret_values(resolved_config)
    start_time = time.time()
    obs, owns_observability = resolve_observability_context(
        observability,
        project_root=resolved_root,
        app_path=getattr(program, "app_path", None),
        config=resolved_config,
    )
    if obs and owns_observability:
        obs.start_session()
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
        flows={flow.name: flow for flow in program.flows},
        flow_contracts=getattr(program, "flow_contracts", {}) or {},
        pipeline_contracts=pipeline_contracts(),
        jobs={job.name: job for job in getattr(program, "jobs", [])},
        job_order=[job.name for job in getattr(program, "jobs", [])],
        capabilities=getattr(program, "capabilities", ()),
        pack_allowlist=getattr(program, "pack_allowlist", None),
        memory_manager=memory_manager,
        runtime_theme=resolution.setting_used.value,
        config=resolved_config,
        policy=getattr(program, "policy", None),
        identity_schema=getattr(program, "identity", None),
        identity=identity,
        auth_context=auth_context,
        session=session,
        project_root=resolved_root,
        app_path=getattr(program, "app_path", None),
        flow_action_id=action_id,
        observability=obs,
        extension_hook_manager=getattr(program, "extension_hook_manager", None),
        app_permissions=getattr(program, "app_permissions", None),
        app_permissions_enabled=bool(getattr(program, "app_permissions_enabled", False)),
        ui_state_scope_by_key=getattr(program, "ui_state_scope_by_key", None),
    )
    module_traces = getattr(program, "module_traces", None)
    if module_traces:
        executor.ctx.traces.extend(copy.deepcopy(module_traces))
    auth_traces = getattr(auth_context, "traces", None)
    auth_source = getattr(auth_context, "source", None)
    if isinstance(auth_traces, list) and auth_traces and auth_source and auth_source != "none":
        executor.ctx.traces.extend(copy.deepcopy(auth_traces))
    actor = actor_summary(executor.ctx.identity)
    status = "ok"
    result: ExecutionResult | None = None
    error: Exception | None = None
    span_id = None
    if obs and owns_observability:
        span_kind = "action" if action_id else "flow"
        span_name = f"action:{action_id}" if action_id else f"flow:{flow_name}"
        timing_labels = {"action": action_id} if action_id else {"flow": flow_name}
        if action_id:
            timing_labels["flow"] = flow_name
        span_id = obs.start_span(
            executor.ctx,
            name=span_name,
            kind=span_kind,
            details={"flow": flow_name, "action_id": action_id},
            timing_name=span_kind,
            timing_labels=timing_labels,
        )
    try:
        result = executor.run()
    except Exception as err:
        status = "error"
        error = err
        if resolved_root and not executor.ctx.sensitive:
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
        if span_id and obs:
            obs.end_span(executor.ctx, span_id, status=status)
        if obs and owns_observability:
            obs.flush()
        if resolved_root and not executor.ctx.sensitive:
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
        if resolved_root and executor.ctx.sensitive:
            from namel3ss.runtime.security.sensitive_audit import record_sensitive_access, resolve_actor

            action_label = "action" if action_id else ("route" if route_name else "flow")
            record_sensitive_access(
                project_root=resolved_root,
                app_path=getattr(program, "app_path", None),
                flow_name=flow_name,
                user=resolve_actor(executor.ctx.identity),
                action=action_label,
                step_count=getattr(executor.ctx, "execution_step_counter", 0),
                route_name=route_name,
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
