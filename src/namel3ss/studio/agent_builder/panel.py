from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from namel3ss.config.loader import load_config
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.payload import build_error_from_exception, build_error_payload
from namel3ss.ir import nodes as ir
from namel3ss.module_loader import load_project
from namel3ss.production_contract import build_run_payload
from namel3ss.runtime.executor.agents import execute_run_agent, execute_run_agents_parallel
from namel3ss.runtime.executor.context import ExecutionContext
from namel3ss.runtime.ai.mock_provider import MockProvider
from namel3ss.runtime.identity.context import resolve_identity
from namel3ss.runtime.memory.api import MemoryManager, admin_action
from namel3ss.runtime.memory_packs import (
    load_memory_pack_catalog,
    merge_packs,
    resolve_pack_selection,
    select_packs,
)
from namel3ss.runtime.memory_packs.config import write_memory_pack_config
from namel3ss.runtime.memory_packs.render import pack_diff_lines
from namel3ss.runtime.run_pipeline import collect_ai_outputs, finalize_run_payload, unwrap_ai_outputs
from namel3ss.runtime.storage.factory import resolve_store
from namel3ss.secrets import collect_secret_values
from namel3ss.studio.agent_builder.selectors import (
    list_agents,
    list_ai_profiles,
    list_memory_packs,
    list_memory_options,
    list_patterns,
    list_tools,
)
from namel3ss.studio.agent_builder.handoff import list_handoffs
from namel3ss.studio.agent_explain import build_agent_explain_payload
from namel3ss.studio.session import SessionState
from namel3ss.studio.trace_adapter import normalize_action_response


@dataclass(frozen=True)
class AgentRunRequest:
    agent_names: list[str]
    message: str
    payload: dict
    parallel: bool


def get_agents_payload(source: str, session: SessionState | None, app_path: str) -> dict:
    try:
        session = session or SessionState()
        app_file = Path(app_path)
        project = load_project(app_file, source_overrides={app_file: source})
        program = project.program
        config = load_config(app_path=app_file)
        memory_manager = _ensure_memory_manager(session, program)
        handoffs = list_handoffs(memory_manager, program)
        selection_app = resolve_pack_selection(config, agent_id=None)
        selection_agents = {
            agent.name: resolve_pack_selection(config, agent_id=agent.name)
            for agent in program.agents.values()
        }
        return {
            "ok": True,
            "agents": list_agents(program),
            "ais": list_ai_profiles(program),
            "tools": list_tools(program),
            "patterns": list_patterns(),
            "memory_presets": list_memory_options(),
            "memory_packs": list_memory_packs(
                project_root=getattr(program, "project_root", None),
                app_path=getattr(program, "app_path", None),
            ),
            "memory_pack_selection": {
                "app": _pack_selection_payload(selection_app),
                "agents": {name: _pack_selection_payload(sel) for name, sel in selection_agents.items()},
            },
            "handoffs": handoffs,
        }
    except Namel3ssError as err:
        return build_error_from_exception(err, kind="agents", source=source)
    except Exception as err:  # pragma: no cover - defensive guard rail
        return build_error_payload(str(err), kind="internal")


def run_agent_payload(source: str, session: SessionState | None, app_path: str, body: dict) -> dict:
    session = session or SessionState()
    app_file = Path(app_path)
    try:
        request = _parse_run_request(body)
        project = load_project(app_file, source_overrides={app_file: source})
        program = project.program
        config = load_config(app_path=app_file)
        identity = resolve_identity(config, getattr(program, "identity", None))
        store = resolve_store(session.ensure_store(config), config=config)
        memory_manager = _ensure_memory_manager(session, program)
        ctx = _build_context(program, store, memory_manager, identity, config, session.state)
        traces: list[dict] = []
        result_value: object | None = None
        if request.parallel and len(request.agent_names) > 1:
            stmt = ir.RunAgentsParallelStmt(
                entries=[
                    ir.ParallelAgentEntry(
                        agent_name=name,
                        input_expr=_literal_input(request.message),
                        line=None,
                        column=None,
                    )
                    for name in request.agent_names
                ],
                target="results",
                line=None,
                column=None,
            )
            execute_run_agents_parallel(ctx, stmt)
            result_value = ctx.locals.get("results")
        else:
            for name in request.agent_names:
                stmt = ir.RunAgentStmt(
                    agent_name=name,
                    input_expr=_literal_input(request.message),
                    target="result",
                    line=None,
                    column=None,
                )
                execute_run_agent(ctx, stmt)
            result_value = ctx.locals.get("result")
        traces = _normalize_traces(ctx.traces)
        outputs = collect_ai_outputs(traces)
        result_value = unwrap_ai_outputs(result_value, outputs)
        secret_values = collect_secret_values(config)
        payload = build_run_payload(
            ok=True,
            flow_name=_flow_name_for_agents(request),
            state=session.state,
            result=result_value,
            traces=traces,
            project_root=getattr(program, "project_root", None),
        )
        payload = finalize_run_payload(payload, secret_values)
        payload["agent_explain"] = build_agent_explain_payload(traces, parallel=request.parallel)
        _persist_memory(memory_manager, program, secret_values)
        return normalize_action_response(payload)
    except Namel3ssError as err:
        error_payload = build_error_from_exception(err, kind="runtime", source=source)
        config = load_config(app_path=app_file)
        secret_values = collect_secret_values(config)
        payload = build_run_payload(
            ok=False,
            flow_name=None,
            state=session.state,
            result=None,
            traces=[],
            project_root=app_file.parent,
            error=err,
            error_payload=error_payload,
        )
        payload = finalize_run_payload(payload, secret_values)
        return normalize_action_response(payload)
    except Exception as err:  # pragma: no cover - defensive guard rail
        error_payload = build_error_payload(str(err), kind="internal")
        payload = build_run_payload(
            ok=False,
            flow_name=None,
            state=session.state,
            result=None,
            traces=[],
            project_root=app_file.parent,
            error=err,
            error_payload=error_payload,
        )
        payload = finalize_run_payload(payload)
        return normalize_action_response(payload)


def run_handoff_action(source: str, session: SessionState | None, app_path: str, body: dict) -> dict:
    session = session or SessionState()
    app_file = Path(app_path)
    try:
        action = str(body.get("action") or "").strip()
        if action not in {"create", "apply"}:
            raise Namel3ssError("Handoff action must be create or apply.")
        project = load_project(app_file, source_overrides={app_file: source})
        program = project.program
        config = load_config(app_path=app_file)
        identity = resolve_identity(config, getattr(program, "identity", None))
        memory_manager = _ensure_memory_manager(session, program)
        secret_values = collect_secret_values(config)
        if action == "create":
            from_agent = str(body.get("from_agent_id") or "").strip()
            to_agent = str(body.get("to_agent_id") or "").strip()
            if not from_agent or not to_agent:
                raise Namel3ssError("Handoff create requires from_agent_id and to_agent_id.")
            ai_profile = _resolve_agent_ai(program, from_agent)
            result = admin_action(
                memory_manager,
                ai_profile,
                session.state,
                "create_handoff",
                payload={"from_agent_id": from_agent, "to_agent_id": to_agent},
                identity=identity,
                project_root=getattr(program, "project_root", None),
                app_path=getattr(program, "app_path", None),
            )
        else:
            packet_id = str(body.get("packet_id") or "").strip()
            if not packet_id:
                raise Namel3ssError("Handoff apply requires packet_id.")
            packet = memory_manager.handoffs.get_packet(packet_id)
            to_agent = packet.to_agent_id if packet else None
            ai_profile = _resolve_agent_ai(program, to_agent) if to_agent else _first_ai_profile(program)
            result = admin_action(
                memory_manager,
                ai_profile,
                session.state,
                "apply_handoff",
                payload={"packet_id": packet_id},
                identity=identity,
                project_root=getattr(program, "project_root", None),
                app_path=getattr(program, "app_path", None),
            )
        traces = _normalize_traces(result.events if hasattr(result, "events") else result.get("events"))
        payload = build_run_payload(
            ok=True,
            flow_name=f"handoff.{action}",
            state=session.state,
            result=getattr(result, "payload", None) if hasattr(result, "payload") else result.get("payload"),
            traces=traces,
            project_root=getattr(program, "project_root", None),
        )
        payload = finalize_run_payload(payload, secret_values)
        payload["agent_explain"] = build_agent_explain_payload(traces, parallel=False)
        _persist_memory(memory_manager, program, secret_values)
        return normalize_action_response(payload)
    except Namel3ssError as err:
        error_payload = build_error_from_exception(err, kind="runtime", source=source)
        payload = build_run_payload(
            ok=False,
            flow_name=None,
            state=session.state,
            result=None,
            traces=[],
            project_root=app_file.parent,
            error=err,
            error_payload=error_payload,
        )
        payload = finalize_run_payload(payload, collect_secret_values(load_config(app_path=app_file)))
        return normalize_action_response(payload)
    except Exception as err:  # pragma: no cover - defensive guard rail
        error_payload = build_error_payload(str(err), kind="internal")
        payload = build_run_payload(
            ok=False,
            flow_name=None,
            state=session.state,
            result=None,
            traces=[],
            project_root=app_file.parent,
            error=err,
            error_payload=error_payload,
        )
        payload = finalize_run_payload(payload)
        return normalize_action_response(payload)


def update_memory_packs(source: str, session: SessionState | None, app_path: str, body: dict) -> dict:
    try:
        session = session or SessionState()
        app_file = Path(app_path)
        project = load_project(app_file, source_overrides={app_file: source})
        program = project.program
        catalog = load_memory_pack_catalog(
            project_root=getattr(program, "project_root", None),
            app_path=getattr(program, "app_path", None),
        )
        available_ids = set(catalog.available.keys())
        default_pack = _parse_pack_value(body.get("default_pack"), available_ids, allow_auto=True)
        overrides_payload = body.get("agent_overrides") if isinstance(body.get("agent_overrides"), dict) else {}
        overrides: dict[str, str] = {}
        for agent_name, value in overrides_payload.items():
            if agent_name not in program.agents:
                raise Namel3ssError(f"Unknown agent '{agent_name}'.")
            override_value = _parse_pack_value(value, available_ids, allow_auto=False, allow_inherit=True)
            if override_value is None:
                continue
            overrides[agent_name] = override_value
        config = load_config(app_path=app_file)
        config.memory_packs.default_pack = default_pack
        config.memory_packs.agent_overrides = overrides
        write_memory_pack_config(app_file.parent, config.memory_packs)
        selection_app = resolve_pack_selection(config, agent_id=None)
        selection_agents = {
            agent.name: resolve_pack_selection(config, agent_id=agent.name)
            for agent in program.agents.values()
        }
        selected_packs = select_packs(catalog, selection=selection_app)
        setup = merge_packs(packs=selected_packs, overrides=catalog.overrides)
        session.memory_manager = None
        return {
            "ok": True,
            "selection": {
                "app": _pack_selection_payload(selection_app),
                "agents": {name: _pack_selection_payload(sel) for name, sel in selection_agents.items()},
            },
            "diff_lines": pack_diff_lines(setup.sources),
        }
    except Namel3ssError as err:
        return build_error_from_exception(err, kind="agents", source=source)
    except Exception as err:  # pragma: no cover - defensive guard rail
        return build_error_payload(str(err), kind="internal")


def _parse_run_request(body: dict) -> AgentRunRequest:
    agents = body.get("agents")
    if isinstance(agents, list):
        agent_names = [str(entry) for entry in agents if entry]
    else:
        agent = body.get("agent")
        agent_names = [str(agent)] if agent else []
    agent_names = [name for name in agent_names if name]
    if not agent_names:
        raise Namel3ssError("Agent run requires at least one agent.")
    message = str(body.get("input") or "").strip()
    if not message:
        raise Namel3ssError("Agent run requires input text.")
    payload = body.get("payload") if isinstance(body.get("payload"), dict) else {}
    parallel = bool(body.get("parallel"))
    agent_names = sorted(set(agent_names))
    return AgentRunRequest(
        agent_names=agent_names,
        message=_merge_input_payload(message, payload),
        payload=payload,
        parallel=parallel,
    )


def _merge_input_payload(message: str, payload: dict) -> str:
    if not payload:
        return message
    payload_text = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return f"{message}\n\npayload: {payload_text}"


def _literal_input(text: str) -> ir.Literal:
    return ir.Literal(value=text, line=None, column=None)


def _normalize_traces(items: Iterable[object] | None) -> list[dict]:
    traces: list[dict] = []
    for item in items or []:
        if isinstance(item, dict):
            traces.append(dict(item))
        else:
            data = getattr(item, "__dict__", None)
            traces.append(dict(data) if isinstance(data, dict) else {"trace": item})
    return traces


def _flow_name_for_agents(request: AgentRunRequest) -> str:
    if len(request.agent_names) == 1:
        return f"agent.{request.agent_names[0]}"
    return "agent.parallel"


def _build_context(
    program: ir.Program,
    store,
    memory_manager: MemoryManager,
    identity: dict,
    config,
    state: dict,
) -> ExecutionContext:
    dummy_flow = ir.Flow(name="agent_panel", body=[], requires=None, audited=False, line=None, column=None)
    schemas = {schema.name: schema for schema in getattr(program, "records", [])}
    provider = MockProvider()
    return ExecutionContext(
        flow=dummy_flow,
        schemas=schemas,
        state=state,
        locals={"input": {}, "secrets": {}},
        identity=identity,
        constants=set(),
        last_value=None,
        store=store,
        ai_provider=provider,
        ai_profiles=program.ais,
        agents=program.agents,
        tools=program.tools,
        functions=getattr(program, "functions", {}),
        traces=list(getattr(program, "module_traces", []) or []),
        memory_manager=memory_manager,
        agent_calls=0,
        config=config,
        provider_cache={"mock": provider},
        runtime_theme=None,
        project_root=getattr(program, "project_root", None),
        app_path=getattr(program, "app_path", None),
        record_changes=[],
        execution_steps=[],
        execution_step_counter=0,
    )


def _ensure_memory_manager(session: SessionState, program: ir.Program) -> MemoryManager:
    if session.memory_manager is None:
        session.memory_manager = MemoryManager(
            project_root=getattr(program, "project_root", None),
            app_path=getattr(program, "app_path", None),
        )
    return session.memory_manager


def _persist_memory(memory_manager: MemoryManager, program: ir.Program, secret_values: list[str]) -> None:
    memory_manager.persist(
        project_root=getattr(program, "project_root", None),
        app_path=getattr(program, "app_path", None),
        secret_values=secret_values,
    )


def _resolve_agent_ai(program: ir.Program, agent_name: str) -> ir.AIDecl:
    agent = program.agents.get(agent_name)
    if agent is None:
        raise Namel3ssError(f"Unknown agent '{agent_name}'.")
    profile = program.ais.get(agent.ai_name)
    if profile is None:
        raise Namel3ssError(f"Agent '{agent_name}' references unknown AI '{agent.ai_name}'.")
    return profile


def _first_ai_profile(program: ir.Program) -> ir.AIDecl:
    if program.ais:
        return program.ais[sorted(program.ais.keys())[0]]
    raise Namel3ssError("No AI profiles available for handoff.")


def _pack_selection_payload(selection) -> dict:
    return {
        "pack_id": getattr(selection, "pack_id", None),
        "mode": getattr(selection, "mode", "auto"),
        "source": getattr(selection, "source", "auto"),
    }


def _parse_pack_value(
    value: object,
    available_ids: set[str],
    *,
    allow_auto: bool,
    allow_inherit: bool = False,
) -> str | None:
    if value is None:
        return None if allow_auto else None
    text = str(value).strip()
    if not text:
        return None if allow_auto else None
    lowered = text.lower()
    if allow_inherit and lowered in {"inherit"}:
        return None
    if allow_auto and lowered in {"auto"}:
        return None
    if lowered in {"none", "off"}:
        return "none"
    if text not in available_ids:
        raise Namel3ssError(f"Memory pack '{text}' was not found.")
    return text


__all__ = ["get_agents_payload", "run_agent_payload", "run_handoff_action", "update_memory_packs"]
