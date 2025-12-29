from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass

from namel3ss.errors.base import Namel3ssError
from namel3ss.ir import nodes as ir
from namel3ss.runtime.memory.manager import MemoryManager
from namel3ss.runtime.memory.proof.admin_actions import (
    _advance_phase,
    _apply_agreement,
    _apply_handoff,
    _compute_impact,
    _create_handoff,
    _propose_rule,
)
from namel3ss.runtime.memory.proof.snapshots import (
    _cache_versions,
    _delta_written,
    _memory_counts,
    _phase_snapshot,
    _snapshot_memory_items,
)

from .scenario import Scenario, ScenarioStep


@dataclass
class ScenarioRun:
    scenario_id: str
    scenario_name: str
    recall_steps: list[dict]
    write_steps: list[dict]
    meta: dict


def run_scenario(scenario: Scenario) -> ScenarioRun:
    manager = MemoryManager()
    state = deepcopy(scenario.initial_state)
    identity = deepcopy(scenario.identity)
    ai_profile = _build_ai_profile(scenario.ai_profile)
    recall_steps: list[dict] = []
    write_steps: list[dict] = []
    recall_hashes: list[dict] = []
    cache_versions_by_step: list[dict] = []
    phase_snapshots_by_step: list[dict] = []
    memory_snapshot = _snapshot_memory_items(manager)

    for step_index, step in enumerate(scenario.steps, start=1):
        if step.kind == "recall":
            recall_step = _run_recall_step(
                manager,
                ai_profile,
                step,
                state=state,
                identity=identity,
                step_index=step_index,
            )
            recall_steps.append(recall_step)
            recall_hashes.append(
                {
                    "step_index": step_index,
                    "deterministic_hash": recall_step.get("deterministic_hash"),
                }
            )
        elif step.kind == "record":
            write_steps.append(
                _run_record_step(
                    manager,
                    ai_profile,
                    step,
                    state=state,
                    identity=identity,
                    step_index=step_index,
                )
            )
        elif step.kind == "admin":
            before_snapshot = memory_snapshot
            admin_step = _run_admin_step(
                manager,
                ai_profile,
                step,
                state=state,
                identity=identity,
                step_index=step_index,
            )
            after_snapshot = _snapshot_memory_items(manager)
            if "written" not in admin_step:
                admin_step["written"] = _delta_written(before_snapshot, after_snapshot)
            write_steps.append(admin_step)
        else:
            raise Namel3ssError(f"Unknown scenario step type: {step.kind}")
        cache_versions_by_step.append(
            {
                "step_index": step_index,
                "versions": _cache_versions(manager),
            }
        )
        phase_snapshots_by_step.append(
            {
                "step_index": step_index,
                "phases": _phase_snapshot(manager),
            }
        )
        memory_snapshot = _snapshot_memory_items(manager)

    meta = {
        "scenario": {
            "id": scenario.scenario_id,
            "name": scenario.name,
        },
        "step_counts": {
            "total": len(scenario.steps),
            "recall": len(recall_steps),
            "record": len([step for step in scenario.steps if step.kind == "record"]),
            "admin": len([step for step in scenario.steps if step.kind == "admin"]),
        },
        "memory_counts": _memory_counts(manager),
        "recall_hashes": recall_hashes,
        "cache_versions_by_step": cache_versions_by_step,
        "phase_snapshots_by_step": phase_snapshots_by_step,
    }
    return ScenarioRun(
        scenario_id=scenario.scenario_id,
        scenario_name=scenario.name,
        recall_steps=recall_steps,
        write_steps=write_steps,
        meta=meta,
    )


def _run_recall_step(
    manager: MemoryManager,
    ai_profile: ir.AIDecl,
    step: ScenarioStep,
    *,
    state: dict,
    identity: dict,
    step_index: int,
) -> dict:
    payload = step.payload
    user_input = payload.get("input")
    agent_id = payload.get("agent_id")
    context, events, meta = manager.recall_context_with_events(
        ai_profile,
        str(user_input),
        state,
        identity=identity,
        agent_id=str(agent_id) if agent_id else None,
    )
    recalled = _flatten_context(context)
    deterministic_hash = manager.recall_hash(recalled)
    return {
        "step_index": step_index,
        "step_kind": "recall",
        "input": user_input,
        "agent_id": agent_id,
        "context": context,
        "events": events,
        "meta": meta,
        "deterministic_hash": deterministic_hash,
    }


def _run_record_step(
    manager: MemoryManager,
    ai_profile: ir.AIDecl,
    step: ScenarioStep,
    *,
    state: dict,
    identity: dict,
    step_index: int,
) -> dict:
    payload = step.payload
    user_input = payload.get("input")
    ai_output = payload.get("output")
    tool_events = payload.get("tool_events", []) or []
    agent_id = payload.get("agent_id")
    written, events = manager.record_interaction_with_events(
        ai_profile,
        state,
        str(user_input),
        str(ai_output),
        list(tool_events),
        identity=identity,
        agent_id=str(agent_id) if agent_id else None,
    )
    return {
        "step_index": step_index,
        "step_kind": "record",
        "input": user_input,
        "output": ai_output,
        "tool_events": tool_events,
        "agent_id": agent_id,
        "written": written,
        "events": events,
    }


def _run_admin_step(
    manager: MemoryManager,
    ai_profile: ir.AIDecl,
    step: ScenarioStep,
    *,
    state: dict,
    identity: dict,
    step_index: int,
) -> dict:
    payload = step.payload
    action = payload.get("action")
    action_payload = payload.get("payload") or {}
    base = {
        "step_index": step_index,
        "step_kind": "admin",
        "action": action,
        "payload": action_payload,
    }
    if action == "propose_rule":
        events = _propose_rule(manager, ai_profile, state, identity, action_payload)
        base["events"] = events
        return base
    if action == "apply_agreement":
        events = _apply_agreement(manager, ai_profile, state, identity, action_payload)
        base["events"] = events
        return base
    if action == "create_handoff":
        events, packet = _create_handoff(manager, ai_profile, state, identity, action_payload)
        base["events"] = events
        if packet:
            base["result"] = {"packet_id": packet.packet_id, "status": packet.status}
        return base
    if action == "apply_handoff":
        events, applied = _apply_handoff(manager, ai_profile, state, identity, action_payload)
        base["events"] = events
        base["written"] = applied
        return base
    if action == "compute_impact":
        impact = _compute_impact(manager, action_payload)
        base["result"] = impact
        base["events"] = []
        return base
    if action == "advance_phase":
        state_update = _advance_phase(state, action_payload, step_index=step_index)
        base["result"] = {"state_update": state_update}
        base["events"] = []
        return base
    raise Namel3ssError(f"Unsupported admin action: {action}")


def _build_ai_profile(spec) -> ir.AIDecl:
    memory = ir.AIMemory(
        short_term=int(spec.memory.short_term),
        semantic=bool(spec.memory.semantic),
        profile=bool(spec.memory.profile),
        line=1,
        column=1,
    )
    return ir.AIDecl(
        name=spec.name,
        model=spec.model,
        provider=spec.provider,
        system_prompt=spec.system_prompt,
        exposed_tools=list(spec.exposed_tools),
        memory=memory,
        line=1,
        column=1,
    )


def _flatten_context(context: dict) -> list[dict]:
    return list(context.get("short_term", [])) + list(context.get("semantic", [])) + list(context.get("profile", []))


__all__ = ["ScenarioRun", "run_scenario"]
