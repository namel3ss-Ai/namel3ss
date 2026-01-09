from __future__ import annotations

from pathlib import Path

from namel3ss.cli.app_loader import load_program
from namel3ss.config.loader import load_config
from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.identity.context import resolve_identity
from namel3ss.runtime.memory.api import MemoryManager, admin_action
from namel3ss.runtime.memory_lanes.context import resolve_team_id
from namel3ss.secrets import collect_secret_values


def create_handoff(payload: dict) -> dict:
    context = _load_context()
    from_agent_id = _require_text(payload, "from_agent_id")
    to_agent_id = _require_text(payload, "to_agent_id")
    ai_profile = _resolve_agent_ai(context["program"], from_agent_id)
    result = admin_action(
        context["memory_manager"],
        ai_profile,
        context["state"],
        "create_handoff",
        payload={"from_agent_id": from_agent_id, "to_agent_id": to_agent_id},
        identity=context["identity"],
        project_root=context["project_root"],
        app_path=context["app_path"],
    )
    _persist_memory(context)
    summary = _coerce_summary(result)
    packet_id = _payload_value(result, "packet_id")
    output = {"summary": summary}
    if packet_id is not None:
        output["packet_id"] = str(packet_id)
    return output


def apply_handoff(payload: dict) -> dict:
    context = _load_context()
    packet_id = _require_text(payload, "packet_id")
    ai_profile = _resolve_apply_profile(
        context["program"],
        context["memory_manager"],
        packet_id,
        context["team_id"],
    )
    result = admin_action(
        context["memory_manager"],
        ai_profile,
        context["state"],
        "apply_handoff",
        payload={"packet_id": packet_id},
        identity=context["identity"],
        project_root=context["project_root"],
        app_path=context["app_path"],
    )
    _persist_memory(context)
    summary = _coerce_summary(result)
    written = _payload_value(result, "written")
    output = {"summary": summary}
    if isinstance(written, list):
        output["written_count"] = len(written)
    return output


def _load_context() -> dict:
    project_root = Path.cwd().resolve()
    app_path = project_root / "app.ai"
    if not app_path.exists():
        raise Namel3ssError("app.ai was not found in the current directory.")
    program, _ = load_program(str(app_path))
    config = load_config(app_path=app_path)
    identity = resolve_identity(config, getattr(program, "identity", None))
    memory_manager = MemoryManager(
        project_root=str(project_root),
        app_path=str(app_path),
    )
    memory_manager.ensure_restored(project_root=str(project_root), app_path=str(app_path))
    team_id = resolve_team_id(project_root=str(project_root), app_path=str(app_path), config=None)
    return {
        "program": program,
        "config": config,
        "identity": identity,
        "memory_manager": memory_manager,
        "project_root": str(project_root),
        "app_path": str(app_path),
        "team_id": team_id,
        "state": {},
    }


def _persist_memory(context: dict) -> None:
    secret_values = collect_secret_values(context["config"])
    context["memory_manager"].persist(
        project_root=context["project_root"],
        app_path=context["app_path"],
        secret_values=secret_values,
    )


def _resolve_agent_ai(program, agent_name: str):
    agent = program.agents.get(agent_name)
    if agent is None:
        raise Namel3ssError(f"Unknown agent '{agent_name}'.")
    profile = program.ais.get(agent.ai_name)
    if profile is None:
        raise Namel3ssError(f"Agent '{agent_name}' references unknown AI '{agent.ai_name}'.")
    return profile


def _resolve_apply_profile(program, memory_manager: MemoryManager, packet_id: str, team_id: str):
    if packet_id in {"first_pending", "auto"}:
        pending = memory_manager.handoffs.list_packets(team_id)
        packet = pending[0] if pending else None
    else:
        packet = memory_manager.handoffs.get_packet(packet_id)
    if packet is None:
        return _first_ai_profile(program)
    return _resolve_agent_ai(program, packet.to_agent_id)


def _first_ai_profile(program):
    if program.ais:
        return program.ais[sorted(program.ais.keys())[0]]
    raise Namel3ssError("No AI profiles available for handoff.")


def _payload_value(result, key: str):
    payload = result.payload if hasattr(result, "payload") else result.get("payload")
    if not isinstance(payload, dict):
        return None
    return payload.get(key)


def _coerce_summary(result) -> str:
    summary = result.summary if hasattr(result, "summary") else result.get("summary")
    return str(summary or "Memory action completed.")


def _require_text(payload: dict, key: str) -> str:
    value = payload.get(key) if isinstance(payload, dict) else None
    if not isinstance(value, str) or not value.strip():
        raise Namel3ssError(f"{key} is required.")
    return value.strip()
