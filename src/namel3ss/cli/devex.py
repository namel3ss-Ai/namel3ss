from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from namel3ss.cli.app_loader import load_program
from namel3ss.cli.app_path import resolve_app_path
from namel3ss.cli.devex_checks import (
    cli_path_check,
    config_sources_check,
    import_path_check,
    optional_dependencies_check,
    persistence_check,
    project_check,
    python_check,
    resolve_target,
    status_icon as _status_icon,
    studio_assets_check,
)
from namel3ss.cli.doctor_models import DoctorCheck
from namel3ss.cli.doctor_python_tools import build_python_tool_checks
from namel3ss.config.loader import ConfigSource, resolve_config
from namel3ss.config.model import AppConfig
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.capabilities.overrides import unsafe_override_enabled
from namel3ss.secrets.discovery import discover_required_secrets


@dataclass(frozen=True)
class ProjectOverrides:
    app_path: str | None = None
    project_root: str | None = None


@dataclass(frozen=True)
class ProjectContext:
    app_path: Path | None
    project_root: Path
    program: object | None
    sources: dict | None
    config: AppConfig
    config_sources: list[ConfigSource]
    discovery_error: Namel3ssError | None
    config_error: Namel3ssError | None
    program_error: Namel3ssError | None


def parse_project_overrides(args: list[str]) -> tuple[ProjectOverrides, list[str]]:
    cleaned: list[str] = []
    app_path = None
    project_root = None
    idx = 0
    while idx < len(args):
        arg = args[idx]
        if arg == "--app":
            if idx + 1 >= len(args):
                raise Namel3ssError(_missing_flag_value("--app"))
            if app_path is not None:
                raise Namel3ssError(_duplicate_flag("--app"))
            app_path = args[idx + 1]
            idx += 2
            continue
        if arg.startswith("--app="):
            if app_path is not None:
                raise Namel3ssError(_duplicate_flag("--app"))
            app_path = arg.split("=", 1)[1]
            idx += 1
            continue
        if arg == "--project":
            if idx + 1 >= len(args):
                raise Namel3ssError(_missing_flag_value("--project"))
            if project_root is not None:
                raise Namel3ssError(_duplicate_flag("--project"))
            project_root = args[idx + 1]
            idx += 2
            continue
        if arg.startswith("--project="):
            if project_root is not None:
                raise Namel3ssError(_duplicate_flag("--project"))
            project_root = arg.split("=", 1)[1]
            idx += 1
            continue
        cleaned.append(arg)
        idx += 1
    return ProjectOverrides(app_path=app_path, project_root=project_root), cleaned


def load_project_context(
    *,
    app_path: str | None,
    project_root: str | None,
    should_load_program: bool = False,
    allow_missing_app: bool = False,
    allow_config_error: bool = False,
    allow_program_error: bool = False,
    allow_legacy_type_aliases: bool = True,
) -> ProjectContext:
    resolved_app = None
    discovery_error = None
    program = None
    program_error = None
    sources = None
    config_error = None

    try:
        resolved_app = resolve_app_path(app_path, project_root=project_root, search_parents=True)
    except Namel3ssError as err:
        if not allow_missing_app:
            raise
        discovery_error = err

    resolved_root = _resolve_project_root(project_root, resolved_app)
    config, config_sources, config_error = _load_config(resolved_app, resolved_root, allow_config_error)
    if allow_config_error and config is None:
        config = AppConfig()

    if should_load_program and resolved_app is not None:
        try:
            program, sources = load_program(resolved_app.as_posix(), allow_legacy_type_aliases=allow_legacy_type_aliases)
        except Namel3ssError as err:
            if not allow_program_error:
                raise
            program_error = err

    return ProjectContext(
        app_path=resolved_app,
        project_root=resolved_root,
        program=program,
        sources=sources,
        config=config or AppConfig(),
        config_sources=config_sources,
        discovery_error=discovery_error,
        config_error=config_error,
        program_error=program_error,
    )


def build_doctor_report(overrides: ProjectOverrides) -> dict[str, Any]:
    context = load_project_context(
        app_path=overrides.app_path,
        project_root=overrides.project_root,
        should_load_program=True,
        allow_missing_app=True,
        allow_config_error=True,
        allow_program_error=True,
    )
    checks: list[DoctorCheck] = [
        python_check(),
        import_path_check(),
        optional_dependencies_check(context.config),
        _provider_env_check(context),
        _config_check(context),
        persistence_check(context.config),
        project_check(context.app_path, context.project_root),
        *_python_tools_checks(context),
        _capability_overrides_check(context),
        studio_assets_check(),
        cli_path_check(),
    ]
    sorted_checks = _sort_checks(checks)
    return {"status": _overall_status(sorted_checks), "checks": [asdict(c) for c in sorted_checks]}


def _python_tools_checks(context: ProjectContext) -> list[DoctorCheck]:
    return build_python_tool_checks(context.app_path)


def _config_check(context: ProjectContext) -> DoctorCheck:
    if context.config_error is not None:
        details = str(context.config_error).splitlines()[0]
        message = f"Config sources failed to load: {details}"
        fix = "Check namel3ss.toml and environment variables."
        return DoctorCheck(
            id="config_sources",
            category="project",
            code="config.sources.invalid",
            status="error",
            message=message,
            fix=fix,
        )
    return config_sources_check(context.config_sources)


def _provider_env_check(context: ProjectContext) -> DoctorCheck:
    if context.program is None:
        message = "Provider config check skipped (app could not be parsed)."
        fix = "Fix app.ai parse errors to validate provider keys."
        return DoctorCheck(
            id="provider_envs",
            category="providers",
            code="providers.missing",
            status="warning",
            message=message,
            fix=fix,
        )
    required = discover_required_secrets(
        context.program,
        context.config,
        target=resolve_target(context.config),
        app_path=context.app_path,
    )
    missing = [secret.name for secret in required if not secret.available]
    if missing:
        message = f"AI provider keys missing: {', '.join(missing)}"
        fix = "Export the keys you plan to use (e.g., NAMEL3SS_OPENAI_API_KEY) or add them to .env."
        status = "warning"
    else:
        message = "AI provider keys detected for this app."
        fix = "No action needed."
        status = "ok"
    return DoctorCheck(
        id="provider_envs",
        category="providers",
        code="providers.missing",
        status=status,
        message=message,
        fix=fix,
    )


def _capability_overrides_check(context: ProjectContext) -> DoctorCheck:
    overrides = context.config.capability_overrides or {}
    if not overrides:
        return DoctorCheck(
            id="capability_overrides",
            category="security",
            code="capabilities.overrides.none",
            status="ok",
            message="Capability overrides: none configured.",
            fix="No action needed.",
        )
    if context.program is None:
        return DoctorCheck(
            id="capability_overrides",
            category="security",
            code="capabilities.overrides.unknown",
            status="warning",
            message="Capability overrides present but app could not be parsed.",
            fix="Fix app.ai parse errors to validate capability overrides.",
        )
    tool_names = set(getattr(context.program, "tools", {}).keys())
    unknown = sorted(name for name in overrides.keys() if name not in tool_names)
    if unknown:
        return DoctorCheck(
            id="capability_overrides",
            category="security",
            code="capabilities.overrides.unknown",
            status="error",
            message=f"Capability overrides reference unknown tools: {', '.join(unknown)}",
            fix="Remove overrides for tools that are not declared in app.ai.",
        )
    unsafe = sorted(name for name, value in overrides.items() if unsafe_override_enabled(value))
    if unsafe:
        return DoctorCheck(
            id="capability_overrides",
            category="security",
            code="capabilities.overrides.unsafe",
            status="warning",
            message=f"Unsafe capability overrides enabled for: {', '.join(unsafe)}",
            fix="Disable allow_unsafe_execution unless this is intentional.",
        )
    return DoctorCheck(
        id="capability_overrides",
        category="security",
        code="capabilities.overrides.ok",
        status="ok",
        message="Capability overrides look valid.",
        fix="No action needed.",
    )


def _overall_status(checks: Iterable[DoctorCheck]) -> str:
    statuses = {c.status for c in checks}
    if "error" in statuses:
        return "error"
    if "warning" in statuses:
        return "warning"
    return "ok"


def _sort_checks(checks: list[DoctorCheck]) -> list[DoctorCheck]:
    order = {
        "environment": 0,
        "project": 1,
        "providers": 2,
        "tools": 3,
        "security": 4,
        "studio": 5,
    }
    return sorted(checks, key=lambda item: (order.get(item.category, 99), item.id))


def _resolve_project_root(project_root: str | None, app_path: Path | None) -> Path:
    if project_root:
        return Path(project_root).resolve()
    if app_path:
        return app_path.resolve().parent
    return Path.cwd().resolve()


def _load_config(
    app_path: Path | None,
    root: Path,
    allow_config_error: bool,
) -> tuple[AppConfig | None, list[ConfigSource], Namel3ssError | None]:
    try:
        config, sources = resolve_config(app_path=app_path, root=root)
        return config, sources, None
    except Namel3ssError as err:
        if not allow_config_error:
            raise
        return None, [], err


def _missing_flag_value(flag: str) -> str:
    return build_guidance_message(
        what=f"{flag} flag is missing a value.",
        why="Project overrides require a path value.",
        fix=f"Pass a path after {flag}.",
        example=f"n3 run {flag} app.ai",
    )


def _duplicate_flag(flag: str) -> str:
    return build_guidance_message(
        what=f"Duplicate {flag} flag provided.",
        why="Only one override is allowed.",
        fix=f"Remove the extra {flag} flag.",
        example=f"n3 run {flag} app.ai",
    )


__all__ = [
    "ProjectContext",
    "ProjectOverrides",
    "build_doctor_report",
    "load_project_context",
    "parse_project_overrides",
    "_status_icon",
]
