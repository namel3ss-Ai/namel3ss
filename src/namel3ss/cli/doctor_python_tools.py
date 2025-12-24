from __future__ import annotations

from pathlib import Path

from namel3ss.cli.doctor_models import DoctorCheck
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.ir.nodes import lower_program
from namel3ss.parser.core import parse
from namel3ss.runtime.tools.bindings import bindings_path, load_tool_bindings
from namel3ss.runtime.tools.entry_validation import validate_python_tool_entry
from namel3ss.utils.slugify import slugify_tool_name
from namel3ss.runtime.tools.python_env import (
    app_venv_path,
    detect_dependency_info,
    lockfile_path,
    resolve_python_env,
)


def build_python_tool_checks() -> list[DoctorCheck]:
    checks: list[DoctorCheck] = []
    app_path = Path.cwd() / "app.ai"
    if not app_path.exists():
        checks.append(
            DoctorCheck(
                id="python_app_root",
                status="warning",
                message="Python tools: app.ai not found in the current directory.",
                fix="Run `n3 app.ai doctor` from the app root or create app.ai first.",
            )
        )
        return checks
    checks.append(
        DoctorCheck(
            id="python_app_root",
            status="ok",
            message=f"Python tools app root: {app_path.parent.as_posix()}",
            fix="No action needed.",
        )
    )
    python_tools = _load_python_tools(app_path, checks)
    _check_python_tool_entries(app_path.parent, python_tools, checks)
    _check_python_deps(app_path.parent, python_tools, checks)
    _check_python_venv(app_path.parent, python_tools, checks)
    _check_python_lockfile(app_path.parent, python_tools, checks)
    return checks


def _load_python_tools(app_path: Path, checks: list[DoctorCheck]) -> list | None:
    try:
        source = app_path.read_text(encoding="utf-8")
    except Exception as err:
        checks.append(
            _guidance_check(
                id="python_tools",
                status="error",
                what="Unable to read app.ai for python tool checks.",
                why=str(err),
                fix="Ensure app.ai is readable and try again.",
                example="n3 app.ai doctor",
            )
        )
        return None
    try:
        program = lower_program(parse(source))
    except Exception as err:
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
    python_tools = [tool for tool in program.tools.values() if tool.kind == "python"]
    if not python_tools:
        checks.append(
            DoctorCheck(
                id="python_tools",
                status="ok",
                message="No python tools declared.",
                fix="No action needed.",
            )
        )
    else:
        checks.append(
            DoctorCheck(
                id="python_tools",
                status="ok",
                message=f"Python tools declared: {len(python_tools)}.",
                fix="No action needed.",
            )
        )
    return python_tools


def _check_python_tool_entries(app_root: Path, python_tools: list | None, checks: list[DoctorCheck]) -> None:
    if python_tools is None:
        checks.append(
            DoctorCheck(
                id="python_tool_entries",
                status="warning",
                message="Python tool binding checks skipped due to parse errors.",
                fix="Resolve app.ai parse errors to validate tool bindings.",
            )
        )
        return
    if not python_tools:
        checks.append(
            DoctorCheck(
                id="python_tool_entries",
                status="ok",
                message="No python tool bindings to validate.",
                fix="No action needed.",
            )
        )
        return
    try:
        bindings = load_tool_bindings(app_root)
    except Namel3ssError as err:
        checks.append(
            DoctorCheck(
                id="python_tool_entries",
                status="error",
                message=str(err),
                fix="Fix the bindings file and re-run doctor.",
            )
        )
        return
    missing = [tool.name for tool in python_tools if tool.name not in bindings]
    unused = [name for name in bindings if name not in {tool.name for tool in python_tools}]
    entries_ok = True
    if missing:
        entries_ok = False
        suggestions = ", ".join(
            f'n3 tools bind \"{name}\" --entry \"tools.{slugify_tool_name(name)}:run\"' for name in missing
        )
        checks.append(
            _guidance_check(
                id="python_tool_entries",
                status="warning",
                what="Python tools are missing bindings.",
                why=f"Missing entries for: {', '.join(missing)}.",
                fix=f"Run `n3 tools bind --from-app` or bind individually ({suggestions}).",
                example='n3 tools bind --from-app',
            )
        )
    for tool in python_tools:
        binding = bindings.get(tool.name)
        try:
            if not binding:
                continue
            validate_python_tool_entry(binding.entry, tool.name, line=tool.line, column=tool.column)
        except Namel3ssError as err:
            entries_ok = False
            checks.append(
                DoctorCheck(
                    id="python_tool_entries",
                    status="error",
                    message=str(err),
                    fix="Fix the tool binding and re-run doctor.",
                )
            )
            return
    if entries_ok:
        checks.append(
            DoctorCheck(
                id="python_tool_entries",
                status="ok",
                message="Python tool bindings look valid.",
                fix="No action needed.",
            )
        )
    if unused:
        checks.append(
            _guidance_check(
                id="python_tool_unused_bindings",
                status="warning",
                what="Unused tool bindings found.",
                why=f"Bindings without declarations: {', '.join(sorted(unused))}.",
                fix="Remove the unused entries or unbind them.",
                example='n3 tools unbind \"unused tool\"',
            )
        )


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
                DoctorCheck(
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
    checks.append(DoctorCheck(id="python_deps", status=status, message=message, fix=fix))


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
            DoctorCheck(
                id="python_venv",
                status="ok",
                message=f"Venv active: {venv_path.as_posix()} ({env_info.python_path}).",
                fix="No action needed.",
            )
        )
        return
    if python_tools:
        checks.append(
            DoctorCheck(
                id="python_venv",
                status="warning",
                message=f"Venv missing; using system python ({env_info.python_path}).",
                fix="Run `n3 deps install` to create a per-app venv.",
            )
        )
        return
    checks.append(
        DoctorCheck(
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
            DoctorCheck(
                id="python_lockfile",
                status="ok",
                message="Lockfile check skipped (no dependency file).",
                fix="No action needed.",
            )
        )
        return
    if lock_path.exists():
        checks.append(
            DoctorCheck(
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


def _guidance_check(*, id: str, status: str, what: str, why: str, fix: str, example: str) -> DoctorCheck:
    return DoctorCheck(
        id=id,
        status=status,
        message=build_guidance_message(what=what, why=why, fix=fix, example=example),
        fix="",
    )


__all__ = ["build_python_tool_checks"]
