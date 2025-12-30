from __future__ import annotations

from pathlib import Path

from namel3ss.cli.app_path import resolve_app_path
from namel3ss.cli.builds import load_build_metadata
from namel3ss.cli.promotion_state import load_state
from namel3ss.cli.targets import parse_target
from namel3ss.cli.targets_store import build_dir
from namel3ss.config.loader import load_config
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.graduation.matrix import build_capability_matrix
from namel3ss.graduation.render import render_graduation_lines, render_summary_lines
from namel3ss.graduation.rules import evaluate_graduation


def run_status_command(args: list[str]) -> int:
    app_arg = _parse_args(args)
    app_path = resolve_app_path(app_arg)
    project_root = app_path.parent
    config = load_config(app_path=app_path)
    state = load_state(project_root)
    active = state.get("active") or {}
    last = state.get("last_promote") or {}
    previous = state.get("previous") or {}
    active_target = active.get("target") or "none"
    active_build = active.get("build_id") or "none"
    lines = [
        f"Active target: {active_target}",
        f"Active build: {active_build}",
        f"Persistence target: {config.persistence.target}",
    ]
    if active_target != "none":
        try:
            spec = parse_target(active_target)
            lines.append(f"Process model: {spec.process_model}")
            lines.append(f"Recommended persistence: {spec.persistence_default}")
        except Exception:
            pass
    if active_target != "none" and active_build != "none":
        build_path = build_dir(project_root, active_target, active_build)
        lines.append(f"Build path: {build_path.as_posix()}")
        try:
            _, meta = load_build_metadata(project_root, active_target, active_build)
            lines.append(f"Build lock status: {meta.get('lockfile_status', 'n/a')}")
        except Exception:
            lines.append("Build metadata: unavailable, re-run build if needed")
    last_target = last.get("target") or "none"
    last_build = last.get("build_id") or "none"
    lines.append(f"Last promote: {last_target} build {last_build}")
    prev_target = previous.get("target") or "none"
    prev_build = previous.get("build_id") or "none"
    lines.append(f"Rollback target: {prev_target} build {prev_build}")
    matrix = build_capability_matrix()
    report = evaluate_graduation(matrix)
    lines.append("Graduation summary")
    lines.extend(render_summary_lines(matrix))
    lines.extend(render_graduation_lines(report))
    print("\n".join(lines))
    return 0


def _parse_args(args: list[str]) -> str | None:
    app_arg = None
    for arg in args:
        if arg.startswith("--"):
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Unknown flag '{arg}'.",
                    why="where/status does not take flags.",
                    fix="Remove the flag and run again.",
                    example="n3 where",
                )
            )
        if app_arg is None:
            app_arg = arg
            continue
        raise Namel3ssError(
            build_guidance_message(
                what="Too many positional arguments.",
                why="where/status accepts at most one app path.",
                fix="Provide a single app.ai path or none.",
                example="n3 where app.ai",
            )
        )
    return app_arg


__all__ = ["run_status_command"]
