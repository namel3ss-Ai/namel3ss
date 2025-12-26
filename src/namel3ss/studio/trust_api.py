from __future__ import annotations

from pathlib import Path
from typing import Any

from namel3ss.cli.explain_mode import _build_explain_payload
from namel3ss.cli.proofs import load_active_proof, read_proof
from namel3ss.cli.promotion_state import load_state
from namel3ss.cli.targets import parse_target
from namel3ss.config.loader import load_config
from namel3ss.governance.verify import run_verify
from namel3ss.module_loader import load_project
from namel3ss.proofs import build_engine_proof
from namel3ss.secrets import collect_secret_values, discover_required_secrets, redact_payload, set_audit_root, set_engine_target
from namel3ss.observe import filter_events, read_events
from namel3ss.cli.observe_mode import _parse_duration


def get_trust_summary_payload(app_path: str) -> dict:
    app_file = Path(app_path)
    project_root = app_file.parent
    config = load_config(app_path=app_file, root=project_root)
    active = load_active_proof(project_root)
    promotion = load_state(project_root)
    engine_target = _resolve_target(project_root, None, active=active, promotion=promotion)
    build_id = _resolve_active_build(active, promotion)
    return {
        "schema_version": 1,
        "engine_target": engine_target,
        "active_proof_id": active.get("proof_id") if isinstance(active, dict) else None,
        "active_pack_id": build_id,
        "active_build_id": build_id,
        "persistence": _persistence_summary(config),
    }


def get_trust_proof_payload(app_path: str) -> dict:
    app_file = Path(app_path)
    project_root = app_file.parent
    active = load_active_proof(project_root)
    proof_id = active.get("proof_id") if isinstance(active, dict) else None
    if not proof_id:
        return {"schema_version": 1, "ok": False, "error": "No active proof recorded."}
    proof = read_proof(project_root, str(proof_id))
    config = load_config(app_path=app_file, root=project_root)
    redacted = redact_payload(proof, collect_secret_values(config))
    return {"schema_version": 1, "ok": True, "proof_id": proof_id, "proof": redacted}


def apply_trust_verify(app_path: str, payload: dict) -> dict:
    if not isinstance(payload, dict):
        return {"schema_version": 1, "status": "error", "error": "Body must be a JSON object."}
    app_file = Path(app_path)
    project_root = app_file.parent
    target_raw = payload.get("target")
    prod = payload.get("prod", True)
    allow_unsafe = payload.get("allow_unsafe", False)
    target = _resolve_target(project_root, target_raw)
    set_engine_target(target)
    set_audit_root(project_root)
    report = run_verify(app_file, target=target, prod=bool(prod), allow_unsafe=bool(allow_unsafe))
    config = load_config(app_path=app_file, root=project_root)
    redacted = redact_payload(report, collect_secret_values(config))
    return redacted if isinstance(redacted, dict) else {"schema_version": 1, "status": "error", "error": "Invalid verify output."}


def get_trust_proof_snapshot(app_path: str, payload: dict | None = None) -> dict:
    app_file = Path(app_path)
    project_root = app_file.parent
    target_raw = None if payload is None else payload.get("target")
    build_id = None if payload is None else payload.get("build_id")
    target = _resolve_target(project_root, target_raw)
    set_engine_target(target)
    set_audit_root(project_root)
    proof_id, proof = build_engine_proof(app_file, target=target, build_id=build_id)
    config = load_config(app_path=app_file, root=project_root)
    redacted = redact_payload(proof, collect_secret_values(config))
    return {"schema_version": 1, "proof_id": proof_id, "proof": redacted}


def get_trust_secrets_payload(app_path: str, target_raw: str | None = None) -> dict:
    app_file = Path(app_path)
    project_root = app_file.parent
    target = _resolve_target(project_root, target_raw)
    set_engine_target(target)
    set_audit_root(project_root)
    project = load_project(app_file)
    config = load_config(app_path=project.app_path, root=project_root)
    refs = discover_required_secrets(project.program, config, target=target, app_path=project.app_path)
    return {
        "schema_version": 1,
        "target": target,
        "secrets": [
            {"name": ref.name, "source": ref.source, "available": ref.available, "target": ref.target}
            for ref in refs
        ],
    }


def get_trust_observe_payload(app_path: str, *, since: str | None, limit: int) -> dict:
    app_file = Path(app_path)
    project_root = app_file.parent
    config = load_config(app_path=app_file, root=project_root)
    set_audit_root(project_root)
    events = read_events(project_root)
    filtered = filter_events(events, _parse_duration(since) if since else None)
    if limit > 0:
        filtered = filtered[-limit:]
    redacted = [redact_payload(event, collect_secret_values(config)) for event in filtered]
    return {"schema_version": 1, "events": redacted}


def get_trust_explain_payload(app_path: str) -> dict:
    app_file = Path(app_path)
    project_root = app_file.parent
    active = load_active_proof(project_root)
    proof_id = active.get("proof_id") if isinstance(active, dict) else None
    proof = read_proof(project_root, proof_id) if proof_id else {}
    payload = _build_explain_payload(app_file, active, proof)
    config = load_config(app_path=app_file, root=project_root)
    redacted = redact_payload(payload, collect_secret_values(config))
    return redacted if isinstance(redacted, dict) else {"schema_version": 1, "status": "error"}


def _resolve_target(
    project_root: Path,
    target_raw: str | None,
    *,
    active: dict | None = None,
    promotion: dict | None = None,
) -> str:
    if target_raw:
        return parse_target(str(target_raw)).name
    if active and isinstance(active, dict) and active.get("target"):
        return str(active.get("target"))
    promotion = promotion or load_state(project_root)
    active_slot = promotion.get("active") or {}
    if active_slot.get("target"):
        return str(active_slot.get("target"))
    return parse_target(None).name


def _resolve_active_build(active: dict, promotion: dict) -> str | None:
    if isinstance(active, dict) and active.get("build_id"):
        return str(active.get("build_id"))
    slot = promotion.get("active") or {}
    return str(slot.get("build_id")) if slot.get("build_id") else None


def _persistence_summary(config) -> dict[str, Any]:
    target = (config.persistence.target or "memory").lower()
    return {"target": target, "descriptor": _persistence_descriptor(config)}


def _persistence_descriptor(config) -> str | None:
    target = (config.persistence.target or "memory").lower()
    if target == "sqlite":
        return config.persistence.db_path
    if target == "postgres":
        return "postgres (url set)" if config.persistence.database_url else "postgres (missing url)"
    if target == "edge":
        return "edge (url set)" if config.persistence.edge_kv_url else "edge (missing url)"
    if target == "memory":
        return "memory"
    return None


__all__ = [
    "apply_trust_verify",
    "get_trust_explain_payload",
    "get_trust_observe_payload",
    "get_trust_proof_payload",
    "get_trust_proof_snapshot",
    "get_trust_secrets_payload",
    "get_trust_summary_payload",
]
