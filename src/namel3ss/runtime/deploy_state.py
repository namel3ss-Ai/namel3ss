from __future__ import annotations

from pathlib import Path

from namel3ss.cli.promotion_state import load_state
from namel3ss.errors.guidance import build_guidance_message


def read_deploy_state(project_root: Path) -> dict:
    state = load_state(project_root)
    return {
        "active": _normalize_slot(state.get("active")),
        "previous": _normalize_slot(state.get("previous")),
        "last_ship": _normalize_slot(state.get("last_promote")),
    }


def evaluate_deploy_status(
    active: dict,
    *,
    active_build_found: bool,
    has_builds: bool,
    suggested_target: str | None,
) -> tuple[str, list[str]]:
    guidance: list[str] = []
    target = suggested_target or "service"
    if active.get("target") and active.get("build_id"):
        if active_build_found:
            return "active", guidance
        guidance.append(
            build_guidance_message(
                what=f"Active build '{active.get('build_id')}' is missing.",
                why="The build folder is missing or was deleted.",
                fix="Rebuild and ship again to restore the active target.",
                example=f"n3 pack --target {active.get('target') or target}",
            )
        )
        return "missing", guidance
    if has_builds:
        guidance.append(
            build_guidance_message(
                what="Builds are ready but not shipped.",
                why="No active promotion is recorded.",
                fix="Promote a build with n3 ship.",
                example=f"n3 ship --to {target}",
            )
        )
        return "ready", guidance
    guidance.append(
        build_guidance_message(
            what="No build is available.",
            why="Build artifacts have not been created yet.",
            fix="Run n3 pack for the target you want to ship.",
            example=f"n3 pack --target {target}",
        )
    )
    return "empty", guidance


def _normalize_slot(raw: object) -> dict:
    if isinstance(raw, dict):
        return {"target": raw.get("target"), "build_id": raw.get("build_id")}
    return {"target": None, "build_id": None}


__all__ = ["evaluate_deploy_status", "read_deploy_state"]
