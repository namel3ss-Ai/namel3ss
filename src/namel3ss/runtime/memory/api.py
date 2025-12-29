from __future__ import annotations

from namel3ss.ir import nodes as ir
from namel3ss.runtime.memory.admin import run_admin_action
from namel3ss.runtime.memory.explain.builder import build_graph
from namel3ss.runtime.memory.explain.normalize import normalize_graph
from namel3ss.runtime.memory.explain.render_plain import render_why
from namel3ss.runtime.memory.manager import MemoryManager as _MemoryManager
from namel3ss.runtime.memory.types import ProofPack

API_VERSION = "memory.v1"
MemoryManager = _MemoryManager


def recall_with_events(
    manager: MemoryManager,
    ai_profile: ir.AIDecl,
    user_input: str,
    state: dict,
    *,
    identity: dict | None = None,
    project_root: str | None = None,
    app_path: str | None = None,
    agent_id: str | None = None,
) -> ProofPack:
    context, events, meta = manager.recall_context_with_events(
        ai_profile,
        user_input,
        state,
        identity=identity,
        project_root=project_root,
        app_path=app_path,
        agent_id=agent_id,
    )
    recalled = _flatten_context(context)
    proof = _proof_for_recall(manager, ai_profile, recalled)
    summary = _summary_recall(context)
    return ProofPack(
        ok=True,
        api_version=API_VERSION,
        payload=context,
        events=list(events or []),
        meta=dict(meta or {}),
        proof=proof,
        summary=summary,
    )


def record_with_events(
    manager: MemoryManager,
    ai_profile: ir.AIDecl,
    state: dict,
    user_input: str,
    ai_output: str,
    tool_events: list[dict],
    *,
    identity: dict | None = None,
    project_root: str | None = None,
    app_path: str | None = None,
    agent_id: str | None = None,
) -> ProofPack:
    written, events = manager.record_interaction_with_events(
        ai_profile,
        state,
        user_input,
        ai_output,
        tool_events,
        identity=identity,
        project_root=project_root,
        app_path=app_path,
        agent_id=agent_id,
    )
    summary = _summary_record(written)
    proof = {"write_count": len(written or [])}
    return ProofPack(
        ok=True,
        api_version=API_VERSION,
        payload=list(written or []),
        events=list(events or []),
        meta={},
        proof=proof,
        summary=summary,
    )


def admin_action(
    manager: MemoryManager,
    ai_profile: ir.AIDecl,
    state: dict,
    action: str,
    payload: dict | None = None,
    *,
    identity: dict | None = None,
    project_root: str | None = None,
    app_path: str | None = None,
    team_id: str | None = None,
) -> ProofPack:
    summary = _summary_admin(action)
    result, events = run_admin_action(
        manager,
        ai_profile,
        state,
        action,
        payload,
        identity=identity,
        project_root=project_root,
        app_path=app_path,
        team_id=team_id,
    )
    return ProofPack(
        ok=True,
        api_version=API_VERSION,
        payload=result,
        events=list(events or []),
        meta={},
        proof={"action": action},
        summary=summary,
    )


def explain_last(proof_pack: dict | ProofPack) -> dict:
    pack = _coerce_pack(proof_pack)
    graph = normalize_graph(build_graph(pack))
    text = render_why(graph)
    data = {
        "summary": dict(graph.summary),
        "node_count": len(graph.nodes),
        "edge_count": len(graph.edges),
    }
    return {
        "graph": graph.as_dict(),
        "text": text,
        "data": data,
    }


def _flatten_context(context: dict) -> list[dict]:
    return list(context.get("short_term", [])) + list(context.get("semantic", [])) + list(context.get("profile", []))


def _coerce_pack(proof_pack: dict | ProofPack) -> dict:
    if isinstance(proof_pack, ProofPack):
        return proof_pack.as_dict()
    if isinstance(proof_pack, dict):
        return proof_pack
    return {}


def _proof_for_recall(manager: MemoryManager, ai_profile: ir.AIDecl, recalled: list[dict]) -> dict:
    proof = {"recall_hash": manager.recall_hash(recalled)}
    phase_mode = _phase_mode(manager, ai_profile)
    if phase_mode:
        proof["phase_mode"] = phase_mode
    return proof


def _phase_mode(manager: MemoryManager, ai_profile: ir.AIDecl) -> str | None:
    policy = manager.policy_for(ai_profile)
    contract = manager.policy_contract_for(policy)
    phase = getattr(contract, "phase", None)
    return getattr(phase, "mode", None)


def _summary_recall(context: dict) -> str:
    counts = _count_context(context)
    total = sum(counts.values())
    item_label = _plural(total, "item")
    parts = []
    if counts["short_term"]:
        parts.append(f"{counts['short_term']} short term")
    if counts["semantic"]:
        parts.append(f"{counts['semantic']} semantic")
    if counts["profile"]:
        parts.append(f"{counts['profile']} profile")
    if parts:
        return f"Recalled {total} {item_label}: {', '.join(parts)}."
    return f"Recalled {total} {item_label}."


def _summary_record(written: list[dict]) -> str:
    count = len(written or [])
    return f"Recorded {count} {_plural(count, 'item')}."


def _summary_admin(action: str) -> str:
    summaries = {
        "propose_rule": "Proposed a memory rule.",
        "apply_agreement": "Applied a memory agreement.",
        "create_handoff": "Created a memory handoff.",
        "apply_handoff": "Applied a memory handoff.",
        "compute_impact": "Computed memory impact.",
        "advance_phase": "Advanced the memory phase.",
    }
    return summaries.get(action, f"Admin action {action} completed.")


def _count_context(context: dict) -> dict[str, int]:
    return {
        "short_term": len(context.get("short_term", [])),
        "semantic": len(context.get("semantic", [])),
        "profile": len(context.get("profile", [])),
    }


def _plural(count: int, noun: str) -> str:
    return noun if count == 1 else f"{noun}s"


__all__ = [
    "API_VERSION",
    "MemoryManager",
    "admin_action",
    "explain_last",
    "recall_with_events",
    "record_with_events",
]
