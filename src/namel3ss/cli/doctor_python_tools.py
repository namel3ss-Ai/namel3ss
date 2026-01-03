from __future__ import annotations

from pathlib import Path

from namel3ss.cli.doctor_models import DoctorCheck
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.module_loader import load_project
from namel3ss.tools.health.analyze import analyze_tool_health
from namel3ss.utils.slugify import slugify_tool_name
from namel3ss.runtime.tools.python_env import (
    app_venv_path,
    detect_dependency_info,
    lockfile_path,
    resolve_python_env,
)


def build_python_tool_checks(app_path: Path | None) -> list[DoctorCheck]:
    checks: list[DoctorCheck] = []
    if not app_path or not app_path.exists():
        checks.append(
            _tool_check(
                id="python_app_root",
                status="warning",
                message="Python tools: app.ai not found in the current directory.",
                fix="Run `n3 app.ai doctor` from the app root or create app.ai first.",
            )
        )
        return checks
    checks.append(
        _tool_check(
            id="python_app_root",
            status="ok",
            message=f"Python tools app root: {app_path.parent.as_posix()}",
            fix="No action needed.",
        )
    )
    project = _load_python_project(app_path, checks)
    python_tools = _collect_python_tools(project, checks) if project else None
    report = analyze_tool_health(project) if project else None
    _check_python_tool_health(app_path.parent, python_tools, report, checks)
    _check_pack_health(report, checks)
    non_pack_tools = _filter_non_pack_tools(python_tools, report)
    _check_python_deps(app_path.parent, non_pack_tools, checks)
    _check_python_venv(app_path.parent, non_pack_tools, checks)
    _check_python_lockfile(app_path.parent, non_pack_tools, checks)
    return checks


def _load_python_project(app_path: Path, checks: list[DoctorCheck]):
    try:
        return load_project(app_path)
    except Namel3ssError as err:
        checks.append(
            _guidance_check(
                id="python_tools",
                status="error",
                what="Unable to parse app.ai for python tool checks.",
                why=str(err).splitlines()[0],
                fix="Fix the parse error before running doctor.",
                example="n3 app.ai check",
            )
        )
        return None


def _collect_python_tools(project, checks: list[DoctorCheck]) -> list | None:
    if project is None:
        checks.append(
            _tool_check(
                id="python_tools",
                status="warning",
                message="Python tool checks skipped due to parse errors.",
                fix="Resolve app.ai parse errors to validate tool bindings.",
            )
        )
        return None
    python_tools = [tool for tool in project.program.tools.values() if tool.kind == "python"]
    if not python_tools:
        checks.append(
            _tool_check(
                id="python_tools",
                status="ok",
                message="No python tools declared.",
                fix="No action needed.",
            )
        )
    else:
        checks.append(
            _tool_check(
                id="python_tools",
                status="ok",
                message=f"Python tools declared: {len(python_tools)}.",
                fix="No action needed.",
            )
        )
    return python_tools


def _check_python_tool_health(
    app_root: Path,
    python_tools: list | None,
    report,
    checks: list[DoctorCheck],
) -> None:
    if python_tools is None or report is None:
        checks.append(
            _tool_check(
                id="python_tool_entries",
                status="warning",
                message="Python tool binding checks skipped due to parse errors.",
                fix="Resolve app.ai parse errors to validate tool bindings.",
            )
        )
        return
    if not python_tools:
        checks.append(
            _tool_check(
                id="python_tool_entries",
                status="ok",
                message="No python tool bindings to validate.",
                fix="No action needed.",
            )
        )
        return
    if not report.bindings_valid:
        checks.append(
            _tool_check(
                id="python_tool_entries",
                status="error",
                message=report.bindings_error or "Bindings file is invalid.",
                fix="Fix the bindings file and re-run doctor.",
            )
        )
        return
    if report.duplicate_decls:
        checks.append(
            _guidance_check(
                id="python_tool_duplicates",
                status="error",
                what="Duplicate tool declarations found.",
                why=f"Duplicates: {', '.join(sorted(report.duplicate_decls))}.",
                fix="Rename or remove the duplicate declarations.",
                example='tool "unique tool":',
            )
        )
    if report.collisions:
        checks.append(
            _guidance_check(
                id="python_tool_collisions",
                status="error",
                what="Tool names collide with tool pack tools.",
                why=f"Collisions: {', '.join(sorted(report.collisions))}.",
                fix="Rename the tools or remove the conflicting bindings.",
                example='n3 tools unbind "conflicting tool"',
            )
        )
    if report.invalid_bindings:
        checks.append(
            _guidance_check(
                id="python_tool_invalid_bindings",
                status="error",
                what="Invalid tool bindings detected.",
                why=f"Bindings: {', '.join(sorted(report.invalid_bindings))}.",
                fix="Update bindings to valid module:function entries.",
                example='n3 tools bind "tool name" --entry "tools.my_tool:run"',
            )
        )
    if report.invalid_runners:
        checks.append(
            _guidance_check(
                id="python_tool_invalid_runners",
                status="error",
                what="Invalid tool runner values detected.",
                why=f"Bindings: {', '.join(sorted(report.invalid_runners))}.",
                fix="Update runner to local, service, or container.",
                example='n3 tools set-runner "tool name" --runner local',
            )
        )
    if report.service_missing_urls:
        checks.append(
            _guidance_check(
                id="python_tool_service_urls",
                status="error",
                what="Service runner bindings are missing URLs.",
                why=f"Bindings: {', '.join(sorted(report.service_missing_urls))}.",
                fix="Set url in tools.yaml or export N3_TOOL_SERVICE_URL.",
                example="N3_TOOL_SERVICE_URL=http://127.0.0.1:8787/tools",
            )
        )
    if report.container_missing_images:
        checks.append(
            _guidance_check(
                id="python_tool_container_images",
                status="error",
                what="Container runner bindings are missing images.",
                why=f"Bindings: {', '.join(sorted(report.container_missing_images))}.",
                fix="Set image in tools.yaml.",
                example='image: "ghcr.io/namel3ss/tools:latest"',
            )
        )
    if report.container_missing_runtime:
        checks.append(
            _guidance_check(
                id="python_tool_container_runtime",
                status="error",
                what="Container runtime is unavailable.",
                why=f"Bindings: {', '.join(sorted(report.container_missing_runtime))}.",
                fix="Install docker/podman or switch to local/service runner.",
                example='n3 tools set-runner "tool name" --runner local',
            )
        )
    if report.missing_bindings:
        suggestions = ", ".join(
            f'n3 tools bind \"{name}\" --entry \"tools.{slugify_tool_name(name)}:run\"'
            for name in report.missing_bindings
        )
        checks.append(
            _guidance_check(
                id="python_tool_entries",
                status="warning",
                what="Python tools are missing bindings.",
                why=f"Missing entries for: {', '.join(report.missing_bindings)}.",
                fix=f"Use Studio Tool Wizard or run `n3 tools bind --auto` (or bind individually: {suggestions}).",
                example='n3 tools bind --auto',
            )
        )
    else:
        checks.append(
            _tool_check(
                id="python_tool_entries",
                status="ok",
                message="Python tool bindings look valid.",
                fix="No action needed.",
            )
        )
    if report.unused_bindings:
        checks.append(
            _guidance_check(
                id="python_tool_unused_bindings",
                status="warning",
                what="Unused tool bindings found.",
                why=f"Bindings without declarations: {', '.join(sorted(report.unused_bindings))}.",
                fix="Remove the unused entries or unbind them.",
                example='n3 tools unbind \"unused tool\"',
            )
        )


def _check_pack_health(report, checks: list[DoctorCheck]) -> None:
    if report is None:
        return
    pack_count = len(report.packs)
    if pack_count == 0:
        checks.append(
            _tool_check(
                id="packs_status",
                status="ok",
                message="No packs installed.",
                fix="No action needed.",
            )
        )
        return
    checks.append(
        _tool_check(
            id="packs_status",
            status="ok",
            message=f"Packs installed: {pack_count}.",
            fix="No action needed.",
        )
    )
    pack_issues = [issue for issue in report.issues if issue.code.startswith("packs.")]
    for idx, issue in enumerate(pack_issues, start=1):
        status = "error" if issue.severity == "error" else "warning"
        checks.append(
            _tool_check(
                id=f"packs_issue_{idx}",
                status=status,
                message=issue.message,
                fix="",
            )
        )


def _filter_non_pack_tools(python_tools: list | None, report) -> list | None:
    if python_tools is None:
        return None
    if not report:
        return python_tools
    pack_names: set[str] = set()
    for name, providers in report.pack_tools.items():
        for provider in providers:
            if provider.source == "builtin_pack" or (provider.verified and provider.enabled):
                pack_names.add(name)
                break
    return [tool for tool in python_tools if tool.name not in pack_names]


def _check_python_deps(app_root: Path, python_tools: list | None, checks: list[DoctorCheck]) -> None:
    dep_info = detect_dependency_info(app_root)
    if dep_info.kind == "none":
        if python_tools:
            checks.append(
                _guidance_check(
                    id="python_deps",
                    status="warning",
                    what="Python tools declared but no dependency file found.",
                    why="Expected pyproject.toml or requirements.txt in the app root.",
                    fix="Add pyproject.toml or requirements.txt before installing deps.",
                    example="echo 'requests==2.31.0' > requirements.txt",
                )
            )
        else:
            checks.append(
                _tool_check(
                    id="python_deps",
                    status="ok",
                    message="Dependency file not found (no python tools declared).",
                    fix="No action needed.",
                )
            )
        return
    detail = dep_info.path.as_posix() if dep_info.path else dep_info.kind
    status = "warning" if dep_info.warning else "ok"
    message = f"Dependencies detected: {dep_info.kind} ({detail})."
    fix = "Run `n3 deps install` if dependencies are missing."
    checks.append(_tool_check(id="python_deps", status=status, message=message, fix=fix))


def _check_python_venv(app_root: Path, python_tools: list | None, checks: list[DoctorCheck]) -> None:
    try:
        env_info = resolve_python_env(app_root)
    except Namel3ssError as err:
        checks.append(
            _guidance_check(
                id="python_venv",
                status="error",
                what="Python venv is invalid.",
                why=str(err).splitlines()[0],
                fix="Recreate the venv with `n3 deps install --force`.",
                example="n3 deps install --force",
            )
        )
        return
    venv_path = app_venv_path(app_root)
    if env_info.env_kind == "venv":
        checks.append(
            _tool_check(
                id="python_venv",
                status="ok",
                message=f"Venv active: {venv_path.as_posix()} ({env_info.python_path}).",
                fix="No action needed.",
            )
        )
        return
    if python_tools:
        checks.append(
            _tool_check(
                id="python_venv",
                status="warning",
                message=f"Venv missing; using system python ({env_info.python_path}).",
                fix="Run `n3 deps install` to create a per-app venv.",
            )
        )
        return
    checks.append(
        _tool_check(
            id="python_venv",
            status="ok",
            message=f"No venv detected; using system python ({env_info.python_path}).",
            fix="No action needed.",
        )
    )


def _check_python_lockfile(app_root: Path, python_tools: list | None, checks: list[DoctorCheck]) -> None:
    dep_info = detect_dependency_info(app_root)
    lock_path = lockfile_path(app_root)
    if dep_info.kind == "none":
        checks.append(
            _tool_check(
                id="python_lockfile",
                status="ok",
                message="Lockfile check skipped (no dependency file).",
                fix="No action needed.",
            )
        )
        return
    if lock_path.exists():
        checks.append(
            _tool_check(
                id="python_lockfile",
                status="ok",
                message=f"Lockfile present: {lock_path.as_posix()}",
                fix="No action needed.",
            )
        )
        return
    checks.append(
        _guidance_check(
            id="python_lockfile",
            status="warning",
            what="Dependency file found but lockfile is missing.",
            why=f"Expected {lock_path.name} in the app root.",
            fix="Run `n3 deps lock` to generate a lockfile.",
            example="n3 deps lock",
        )
    )


def _tool_check(*, id: str, status: str, message: str, fix: str) -> DoctorCheck:
    return DoctorCheck(
        id=id,
        status=status,
        message=message,
        fix=fix,
        category="tools",
    )


def _guidance_check(*, id: str, status: str, what: str, why: str, fix: str, example: str) -> DoctorCheck:
    return _tool_check(
        id=id,
        status=status,
        message=build_guidance_message(what=what, why=why, fix=fix, example=example),
        fix="",
    )


__all__ = ["build_python_tool_checks"]
