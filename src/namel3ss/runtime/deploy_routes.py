from __future__ import annotations

from pathlib import Path

from namel3ss.cli.targets import target_names
from namel3ss.cli.targets_store import BUILD_BASE_DIR
from namel3ss.config.loader import ConfigSource, resolve_config
from namel3ss.errors.base import Namel3ssError
from namel3ss.observability.scrub import scrub_payload
from namel3ss.runtime.build_store import latest_build_ids, load_build_summary
from namel3ss.runtime.deploy_state import evaluate_deploy_status, read_deploy_state
from namel3ss.runtime.environment_summary import build_environment_summary
from namel3ss.secrets import collect_secret_values


def get_build_payload(
    project_root: str | Path | None,
    app_path: str | Path | None,
    *,
    config: object | None = None,
    sources: list[ConfigSource] | None = None,
) -> dict:
    root_path = _coerce_path(project_root)
    app_file = _coerce_path(app_path)
    if root_path is None:
        return {"ok": False, "error": "Project root is required."}
    config, sources = _resolve_config(root_path, app_file, config=config, sources=sources)
    secret_values = collect_secret_values(config)
    targets = target_names()
    build_ids = latest_build_ids(root_path, targets)
    builds: list[dict] = []
    guidance: list[str] = []
    for target in targets:
        build_id = build_ids.get(target)
        entry = {"target": target, "build_id": build_id, "status": "missing"}
        if build_id:
            try:
                entry.update(load_build_summary(root_path, target, build_id))
                entry["status"] = "ready"
            except Namel3ssError as err:
                entry["error"] = str(err)
                guidance.append(str(err))
        else:
            guidance.append(_missing_build_message(target))
        builds.append(entry)
    payload: dict[str, object] = {"ok": True, "build_root": BUILD_BASE_DIR, "builds": builds}
    if guidance:
        payload["guidance"] = guidance
    return _scrub(payload, secret_values=secret_values, project_root=project_root, app_path=app_path)


def get_deploy_payload(
    project_root: str | Path | None,
    app_path: str | Path | None,
    *,
    program: object | None = None,
    config: object | None = None,
    sources: list[ConfigSource] | None = None,
    target: str | None = None,
) -> dict:
    root_path = _coerce_path(project_root)
    app_file = _coerce_path(app_path)
    if root_path is None:
        return {"ok": False, "error": "Project root is required."}
    config, sources = _resolve_config(root_path, app_file, config=config, sources=sources)
    secret_values = collect_secret_values(config)
    targets = target_names()
    build_ids = latest_build_ids(root_path, targets)
    state = read_deploy_state(root_path)
    active = state.get("active") or {"target": None, "build_id": None}
    previous = state.get("previous") or {"target": None, "build_id": None}
    last_ship = state.get("last_ship") or {"target": None, "build_id": None}
    active_build = None
    active_build_found = False
    guidance: list[str] = []
    if active.get("target") and active.get("build_id"):
        try:
            active_build = load_build_summary(root_path, str(active["target"]), str(active["build_id"]))
            active_build_found = True
        except Namel3ssError as err:
            guidance.append(str(err))
    status, status_guidance = evaluate_deploy_status(
        active,
        active_build_found=active_build_found,
        has_builds=any(build_ids.values()),
        suggested_target=_suggest_target(build_ids),
    )
    guidance.extend(status_guidance)
    latest_list = [
        {"target": target_name, "build_id": build_ids.get(target_name)} for target_name in targets
    ]
    environment = build_environment_summary(
        project_root,
        app_path,
        program=program,
        config=config,
        sources=sources,
        target=target,
    )
    payload: dict[str, object] = {
        "ok": True,
        "status": status,
        "active": active,
        "previous": previous,
        "last_ship": last_ship,
        "rollback_available": bool(previous.get("build_id")),
        "active_build": active_build,
        "latest": latest_list,
        "environment": environment,
    }
    if guidance:
        payload["guidance"] = guidance
    return _scrub(payload, secret_values=secret_values, project_root=project_root, app_path=app_path)


def _missing_build_message(target: str) -> str:
    return (
        f"What happened: No build found for target '{target}'.\n"
        "Why: Build artifacts have not been created yet.\n"
        "Fix: Run n3 pack for this target.\n"
        f"Example: n3 pack --target {target}"
    )


def _resolve_config(
    project_root: Path,
    app_file: Path | None,
    *,
    config: object | None,
    sources: list[ConfigSource] | None,
) -> tuple[object | None, list[ConfigSource]]:
    if config is not None and sources is not None:
        return config, sources
    resolved_config, resolved_sources = resolve_config(app_path=app_file, root=project_root)
    return resolved_config, resolved_sources


def _suggest_target(build_ids: dict[str, str | None]) -> str | None:
    for candidate in ("service", "local", "edge"):
        if build_ids.get(candidate):
            return candidate
    return None


def _scrub(payload: dict, *, secret_values: list[str], project_root: str | Path | None, app_path: str | Path | None) -> dict:
    cleaned = scrub_payload(payload, secret_values=secret_values, project_root=project_root, app_path=app_path)
    return cleaned if isinstance(cleaned, dict) else payload


def _coerce_path(value: str | Path | None) -> Path | None:
    if value is None:
        return None
    return Path(value)


__all__ = ["get_build_payload", "get_deploy_payload"]
