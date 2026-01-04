from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from namel3ss.cli.proofs import load_active_proof
from namel3ss.cli.promotion_state import load_state
from namel3ss.cli.targets import parse_target
from namel3ss.config.loader import load_config
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.ir import nodes as ir
from namel3ss.module_loader import load_project


@dataclass(frozen=True)
class LearningContext:
    app_path: Path
    project_root: Path
    program: ir.Program
    modules: dict
    graph: object
    engine_target: str
    proof_id: str | None
    verify_status: str | None
    persistence: dict


def build_learning_context(app_path: Path) -> LearningContext:
    project_root = app_path.parent
    project = load_project(app_path)
    config = load_config(app_path=app_path, root=project_root)
    active = load_active_proof(project_root)
    proof_id = active.get("proof_id") if isinstance(active, dict) else None
    engine_target = _resolve_target(project_root, active if isinstance(active, dict) else {})
    verify_status = _load_verify_status(project_root)
    persistence = _persistence_summary(config)
    return LearningContext(
        app_path=app_path,
        project_root=project_root,
        program=project.program,
        modules=project.modules,
        graph=project.graph,
        engine_target=engine_target,
        proof_id=proof_id,
        verify_status=verify_status,
        persistence=persistence,
    )


def require_app_path(app_path: Path) -> None:
    if not app_path.exists():
        raise Namel3ssError(
            build_guidance_message(
                what="app.ai was not found.",
                why=f"Expected {app_path.as_posix()} to exist.",
                fix="Provide the correct app.ai path.",
                example="n3 explain app.ai",
            )
        )


def _resolve_target(project_root: Path, active: dict) -> str:
    if active.get("target"):
        return str(active.get("target"))
    promotion = load_state(project_root)
    slot = promotion.get("active") or {}
    if slot.get("target"):
        return str(slot.get("target"))
    return parse_target(None).name


def _load_verify_status(project_root: Path) -> str | None:
    verify_path = project_root / ".namel3ss" / "verify.json"
    if not verify_path.exists():
        return None
    try:
        data = json.loads(verify_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return "unknown"
    if not isinstance(data, dict):
        return "unknown"
    status = data.get("status")
    return str(status) if status else "unknown"


def _persistence_summary(config) -> dict:
    target = (config.persistence.target or "memory").lower()
    descriptor = None
    if target == "sqlite":
        descriptor = config.persistence.db_path
    elif target == "postgres":
        descriptor = "postgres url set" if config.persistence.database_url else "postgres url missing"
    elif target == "edge":
        descriptor = "edge url set" if config.persistence.edge_kv_url else "edge url missing"
    elif target == "memory":
        descriptor = "memory"
    return {"target": target, "descriptor": descriptor}


__all__ = ["LearningContext", "build_learning_context", "require_app_path"]
