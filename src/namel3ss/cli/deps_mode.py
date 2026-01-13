from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable

from namel3ss.cli.app_path import resolve_app_path
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.tools.python_env import (
    LOCKFILE_NAME,
    REQUIREMENTS_FILE,
    PYPROJECT_FILE,
    app_venv_path,
    build_deps_status,
    detect_dependency_info,
    load_pyproject_dependencies,
    lockfile_path,
    resolve_python_env,
)
from namel3ss.secrets import collect_secret_values, redact_text
from namel3ss.utils.json_tools import dumps, dumps_pretty


def run_deps(args: list[str]) -> int:
    if not args or args[0] in {"help", "-h", "--help"}:
        _print_usage()
        return 0
    app_path, args = _split_app_path(args)
    resolved_app = resolve_app_path(app_path)
    app_root = resolved_app.parent

    cmd = args[0]
    tail = args[1:]
    json_mode = "--json" in tail
    tail = [item for item in tail if item != "--json"]

    if cmd == "status":
        return _run_status(app_root, json_mode=json_mode)
    if cmd == "install":
        return _run_install(app_root, tail, json_mode=json_mode)
    if cmd == "sync":
        return _run_sync(app_root, tail, json_mode=json_mode)
    if cmd == "lock":
        return _run_lock(app_root, tail, json_mode=json_mode)
    if cmd == "clean":
        return _run_clean(app_root, tail, json_mode=json_mode)

    raise Namel3ssError(
        build_guidance_message(
            what=f"Unknown deps command '{cmd}'.",
            why="Supported commands are status, install, sync, lock, and clean.",
            fix="Run `n3 deps help` to see usage.",
            example="n3 deps status",
        )
    )


def _split_app_path(args: list[str]) -> tuple[str | None, list[str]]:
    if args and args[0].endswith(".ai"):
        return args[0], args[1:]
    return None, args


def _run_status(app_root: Path, *, json_mode: bool) -> int:
    status = build_deps_status(app_root)
    dep_info = status.dependency_info
    payload = {
        "app_root": str(status.app_root),
        "venv_path": str(status.venv_path),
        "exists": status.venv_exists,
        "python_path": str(status.python_path),
        "dependency_file_detected": str(dep_info.path) if dep_info.path else None,
        "lockfile_detected": str(status.lockfile_path) if status.lockfile_path else None,
        "last_install_time": status.last_install_time,
        "deps_source": dep_info.kind,
    }
    if dep_info.warning:
        payload["warning"] = dep_info.warning

    if json_mode:
        print(dumps_pretty(payload))
        return 0

    print(f"App root: {payload['app_root']}")
    venv_status = "present" if payload["exists"] else "missing"
    print(f"Venv: {payload['venv_path']} status {venv_status}")
    print(f"Python: {payload['python_path']}")
    print(f"Dependencies: {payload['dependency_file_detected'] or 'none'}")
    print(f"Lockfile: {payload['lockfile_detected'] or 'none'}")
    print(f"Last install: {payload['last_install_time'] or 'unknown'}")
    if dep_info.warning:
        print(f"Warning: {dep_info.warning}")
    return 0


def _run_install(app_root: Path, tail: list[str], *, json_mode: bool) -> int:
    force = "--force" in tail
    dry_run = "--dry-run" in tail or "--plan" in tail
    python_override = _read_flag_value(tail, "--python")
    dep_info = detect_dependency_info(app_root)
    if dep_info.kind == "none":
        raise Namel3ssError(_missing_deps_message())
    if dep_info.warning and not json_mode:
        print(f"Warning: {dep_info.warning}")
    if dry_run:
        payload = _build_install_plan(app_root, dep_info, python_override, force=force)
        if dep_info.warning:
            payload["warning"] = dep_info.warning
        if json_mode:
            print(dumps(payload, indent=2, sort_keys=True))
            return 0
        _print_install_plan(payload)
        return 0
    if force:
        _remove_venv(app_root)
    if not app_venv_path(app_root).exists():
        _create_venv(app_root, python_override)
    env = resolve_python_env(app_root)
    _install_dependencies(app_root, dep_info, env.python_path, force=force)
    lock_path = _write_lockfile(env.python_path, app_root)

    payload = {
        "status": "ok",
        "venv_path": str(app_venv_path(app_root)),
        "python_path": str(env.python_path),
        "deps_source": dep_info.kind,
        "lockfile": str(lock_path),
    }
    if dep_info.warning:
        payload["warning"] = dep_info.warning
    if json_mode:
        print(dumps_pretty(payload))
        return 0
    print("Dependencies installed.")
    print(f"Lockfile: {lock_path}")
    return 0


def _run_sync(app_root: Path, tail: list[str], *, json_mode: bool) -> int:
    if tail:
        raise Namel3ssError("sync does not accept extra arguments")
    lock_path = lockfile_path(app_root)
    if not lock_path.exists():
        return _run_install(app_root, [], json_mode=json_mode)
    if not app_venv_path(app_root).exists():
        _create_venv(app_root, None)
    env = resolve_python_env(app_root)
    _run_pip_command(
        [str(env.python_path), "-m", "pip", "install", "-r", str(lock_path)],
        app_root=app_root,
        action="sync",
    )
    payload = {
        "status": "ok",
        "venv_path": str(app_venv_path(app_root)),
        "python_path": str(env.python_path),
        "lockfile": str(lock_path),
    }
    if json_mode:
        print(dumps_pretty(payload))
        return 0
    print("Dependencies synced.")
    return 0


def _run_lock(app_root: Path, tail: list[str], *, json_mode: bool) -> int:
    if tail:
        raise Namel3ssError("lock does not accept extra arguments")
    dep_info = detect_dependency_info(app_root)
    if dep_info.kind == "none":
        raise Namel3ssError(_missing_deps_message())
    if dep_info.warning and not json_mode:
        print(f"Warning: {dep_info.warning}")
    if not app_venv_path(app_root).exists():
        _create_venv(app_root, None)
    env = resolve_python_env(app_root)
    _install_dependencies(app_root, dep_info, env.python_path, force=False)
    lock_path = _write_lockfile(env.python_path, app_root)
    payload = {
        "status": "ok",
        "venv_path": str(app_venv_path(app_root)),
        "python_path": str(env.python_path),
        "lockfile": str(lock_path),
    }
    if dep_info.warning:
        payload["warning"] = dep_info.warning
    if json_mode:
        print(dumps_pretty(payload))
        return 0
    print(f"Lockfile written: {lock_path}")
    return 0


def _run_clean(app_root: Path, tail: list[str], *, json_mode: bool) -> int:
    yes = "--yes" in tail
    if not yes and not json_mode:
        response = input("Remove .venv and tool caches? y or N ").strip().lower()
        if response not in {"y", "yes"}:
            print("Aborted.")
            return 0
    removed = []
    venv_path = app_venv_path(app_root)
    if venv_path.exists():
        shutil.rmtree(venv_path)
        removed.append(str(venv_path))
    tool_cache = app_root / "tools" / "__pycache__"
    if tool_cache.exists():
        shutil.rmtree(tool_cache)
        removed.append(str(tool_cache))
    payload = {"status": "ok", "removed": removed}
    if json_mode:
        print(dumps_pretty(payload))
        return 0
    if removed:
        print("Removed:")
        for item in removed:
            print(f"- {item}")
    else:
        print("Nothing to clean.")
    return 0


def _create_venv(app_root: Path, python_override: str | None) -> None:
    python_path = Path(python_override) if python_override else Path(_system_python())
    if not python_path.exists():
        raise Namel3ssError(
            build_guidance_message(
                what="Python interpreter not found.",
                why=f"Path '{python_path}' does not exist.",
                fix="Provide a valid interpreter path with --python.",
                example="n3 deps install --python /usr/bin/python3",
            )
        )
    venv_path = app_venv_path(app_root)
    _run_subprocess(
        [str(python_path), "-m", "venv", str(venv_path)],
        app_root=app_root,
        action="create venv",
    )


def _install_dependencies(app_root: Path, dep_info, python_path: Path, *, force: bool) -> None:
    pip_args = [str(python_path), "-m", "pip", "install"]
    if force:
        pip_args.append("--upgrade")
    if dep_info.kind == "requirements":
        req_path = app_root / REQUIREMENTS_FILE
        pip_args.extend(["-r", str(req_path)])
        _run_pip_command(pip_args, app_root=app_root, action="install")
        return
    deps = load_pyproject_dependencies(dep_info.path)
    if not deps:
        return
    pip_args.extend(deps)
    _run_pip_command(pip_args, app_root=app_root, action="install")


def _write_lockfile(python_path: Path, app_root: Path) -> Path:
    result = _run_pip_command(
        [str(python_path), "-m", "pip", "freeze"],
        app_root=app_root,
        action="freeze",
        capture=True,
    )
    lines = [line for line in (result or "").splitlines() if line.strip()]
    lines.sort()
    lock_path = lockfile_path(app_root)
    lock_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return lock_path


def _run_pip_command(
    cmd: list[str],
    *,
    app_root: Path,
    action: str,
    capture: bool = False,
) -> str | None:
    return _run_subprocess(cmd, app_root=app_root, action=action, capture=capture)


def _run_subprocess(
    cmd: list[str],
    *,
    app_root: Path,
    action: str,
    capture: bool = False,
) -> str | None:
    env = os.environ.copy()
    env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    try:
        result = subprocess.run(
            cmd,
            cwd=str(app_root),
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
    except FileNotFoundError as err:
        raise Namel3ssError(
            build_guidance_message(
                what=f"Failed to {action} dependencies.",
                why=str(err),
                fix="Check your python path or reinstall Python.",
                example="n3 deps install --python /usr/bin/python3",
            )
        ) from err
    if result.returncode != 0:
        secret_values = collect_secret_values()
        stderr = redact_text(result.stderr or result.stdout or "", secret_values)
        fix = "Check the dependency file and rerun the command."
        if action == "install":
            fix = f"{fix} Use --dry-run to see the plan without installing."
        raise Namel3ssError(
            build_guidance_message(
                what=f"Dependency {action} failed.",
                why=stderr.strip() or "The subprocess returned a non-zero exit code.",
                fix=fix,
                example="n3 deps install --force",
            )
        )
    if capture:
        return result.stdout
    return None


def _missing_deps_message() -> str:
    return build_guidance_message(
        what="No dependency file found.",
        why=f"Expected {PYPROJECT_FILE} or {REQUIREMENTS_FILE} in the app root.",
        fix="Create a dependency file before running deps commands.",
        example="echo 'requests==2.31.0' > requirements.txt",
    )


def _system_python() -> str:
    return os.environ.get("PYTHON", sys.executable)


def _build_install_plan(app_root: Path, dep_info, python_override: str | None, *, force: bool) -> dict:
    venv_path = app_venv_path(app_root)
    venv_exists = venv_path.exists()
    actions: list[dict] = []
    if force and venv_exists:
        actions.append(
            {
                "action": "remove-venv",
                "path": str(venv_path),
                "would_install": False,
            }
        )
        venv_exists = False
    if not venv_exists:
        python_path = _planned_python_path(python_override)
        actions.append(
            {
                "action": "create-venv",
                "path": str(venv_path),
                "python_path": str(python_path),
                "would_install": False,
            }
        )
    else:
        env = resolve_python_env(app_root)
        python_path = env.python_path
    deps = _collect_dependencies(dep_info)
    actions.append(
        {
            "action": "install-deps",
            "deps_source": dep_info.kind,
            "dependency_file": str(dep_info.path),
            "requirements": deps,
            "would_install": bool(deps),
        }
    )
    actions.append(
        {
            "action": "write-lockfile",
            "path": str(lockfile_path(app_root)),
            "would_install": False,
        }
    )
    return {
        "status": "ok",
        "mode": "dry-run",
        "app_root": str(app_root),
        "venv_path": str(venv_path),
        "python_path": str(python_path),
        "deps_source": dep_info.kind,
        "dependency_file": str(dep_info.path),
        "actions": actions,
        "errors": [],
    }


def _planned_python_path(python_override: str | None) -> Path:
    python_path = Path(python_override) if python_override else Path(_system_python())
    if not python_path.exists():
        raise Namel3ssError(
            build_guidance_message(
                what="Python interpreter not found.",
                why=f"Path '{python_path}' does not exist.",
                fix="Provide a valid interpreter path with --python.",
                example="n3 deps install --python /usr/bin/python3",
            )
        )
    return python_path


def _collect_dependencies(dep_info) -> list[str]:
    if dep_info.kind == "requirements" and dep_info.path:
        return _read_requirements(dep_info.path)
    if dep_info.kind == "pyproject" and dep_info.path:
        return load_pyproject_dependencies(dep_info.path)
    return []


def _read_requirements(path: Path) -> list[str]:
    entries: list[str] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "#" in line:
            line = line.split("#", 1)[0].strip()
        if line:
            entries.append(line)
    return entries


def _print_install_plan(payload: dict) -> None:
    print("Dependency install plan:")
    for action in payload.get("actions", []):
        label = action.get("action", "unknown")
        suffix = " (would install)" if action.get("would_install") else ""
        print(f"- {label}{suffix}")


def _read_flag_value(flags: Iterable[str], name: str) -> str | None:
    items = list(flags)
    for idx, item in enumerate(items):
        if item == name and idx + 1 < len(items):
            return items[idx + 1]
    return None


def _remove_venv(app_root: Path) -> None:
    venv_path = app_venv_path(app_root)
    if venv_path.exists():
        shutil.rmtree(venv_path)


def _print_usage() -> None:
    usage = """Usage:
  n3 deps status --json            # show python env status
  n3 deps install --force --python PATH --dry-run --json
  n3 deps install --plan --json    # alias for --dry-run
  n3 deps sync --json              # install from lockfile if present
  n3 deps lock --json              # write requirements.lock.txt
  n3 deps clean --yes --json       # remove .venv and caches
  Notes:
    flags are optional unless stated
"""
    print(usage.strip())


__all__ = ["run_deps"]
