from __future__ import annotations

from pathlib import Path

from namel3ss.cli.app_path import resolve_app_path
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.pkg.unified_manager import (
    dependency_add,
    dependency_audit,
    dependency_clean,
    dependency_install,
    dependency_status,
    dependency_tree,
    dependency_update,
    dependency_verify,
)
from namel3ss.pkg.runtime_manifest_ops import remove_runtime_dependency
from namel3ss.runtime.capabilities.feature_gate import require_app_capability
from namel3ss.utils.json_tools import dumps_pretty


DEPENDENCY_MANAGEMENT_CAPABILITY = "dependency_management"


def run_dependency_root(command: str, args: list[str]) -> int:
    app_path, tail = _split_app_path(args)
    app_file = resolve_app_path(app_path)
    project_root = app_file.parent
    json_mode = "--json" in tail
    tail = [item for item in tail if item != "--json"]

    _require_dependency_management_capability(app_file)
    payload = _dispatch(command, project_root, tail)
    if json_mode:
        print(dumps_pretty(payload))
        return 0 if payload.get("status") != "fail" else 1
    _print_human(command, payload)
    return 0 if payload.get("status") != "fail" else 1


def run_dependency_subcommand(app_root: Path, command: str, args: list[str], *, json_mode: bool) -> int:
    app_file = app_root / "app.ai"
    _require_dependency_management_capability(app_file)
    payload = _dispatch(command, app_root, list(args))
    if json_mode:
        print(dumps_pretty(payload))
        return 0 if payload.get("status") != "fail" else 1
    _print_human(command, payload)
    return 0 if payload.get("status") != "fail" else 1


def _dispatch(command: str, root: Path, args: list[str]) -> dict[str, object]:
    cmd = str(command or "").strip().lower()
    python_override = _read_flag_value(args, "--python")

    if cmd == "add":
        dependency_type = "system" if "--system" in args else "python"
        values = [item for item in args if item not in {"--system"}]
        if not values:
            raise Namel3ssError(
                build_guidance_message(
                    what="Dependency spec is missing.",
                    why="add requires a runtime dependency string.",
                    fix="Pass a dependency like requests@2.31.0.",
                    example="n3 deps add requests@2.31.0",
                )
            )
        return dependency_add(root, spec=values[0], dependency_type=dependency_type)
    if cmd == "remove":
        dependency_type = "system" if "--system" in args else "python"
        values = [item for item in args if item not in {"--system"}]
        if not values:
            raise Namel3ssError(
                build_guidance_message(
                    what="Dependency spec is missing.",
                    why="remove requires a runtime dependency string.",
                    fix="Pass a dependency like requests==2.31.0.",
                    example="n3 deps remove requests==2.31.0",
                )
            )
        return remove_runtime_dependency(root, spec=values[0], dependency_type=dependency_type)

    if cmd == "install":
        return dependency_install(
            root,
            python_override=python_override,
            include_packages="--skip-packages" not in args,
            include_python="--skip-python" not in args,
        )

    if cmd == "update":
        return dependency_update(root, python_override=python_override)

    if cmd == "status":
        return dependency_status(root)

    if cmd == "tree":
        return dependency_tree(root)

    if cmd == "verify":
        return dependency_verify(root)

    if cmd == "audit":
        return dependency_audit(root)

    if cmd == "clean":
        return dependency_clean(root, include_venv=("--include-venv" in args))

    raise Namel3ssError(
        build_guidance_message(
            what=f"Unknown dependency command '{command}'.",
            why="Supported commands are add, remove, install, update, status, tree, verify, audit, and clean.",
            fix="Run `n3 deps help` to review available commands.",
            example="n3 deps status",
        )
    )


def _split_app_path(args: list[str]) -> tuple[str | None, list[str]]:
    if args and args[0].endswith(".ai"):
        return args[0], args[1:]
    return None, args


def _read_flag_value(args: list[str], name: str) -> str | None:
    for index, item in enumerate(args):
        if item == name and index + 1 < len(args):
            return args[index + 1]
    return None


def _require_dependency_management_capability(app_file: Path) -> None:
    require_app_capability(app_file, DEPENDENCY_MANAGEMENT_CAPABILITY)


def _print_human(command: str, payload: dict[str, object]) -> None:
    cmd = str(command or "").strip().lower()
    if cmd == "status":
        print("Dependency status")
        print(f"manifest: {payload.get('manifest_path')}")
        print(f"lockfile: {payload.get('lockfile_path') or 'missing'}")
        print(f"python lockfile: {payload.get('python_lockfile_path') or 'missing'}")
        print(f"packages: {payload.get('packages_count', 0)}")
        print(f"runtime python: {payload.get('runtime_python_count', 0)}")
        print(f"runtime system: {payload.get('runtime_system_count', 0)}")
        return
    if cmd == "tree":
        package_tree = payload.get("package_tree")
        if isinstance(package_tree, list) and package_tree:
            print("Package tree")
            for line in package_tree:
                print(str(line))
        else:
            print("Package tree: empty")
        runtime_python = payload.get("runtime_python")
        if isinstance(runtime_python, list) and runtime_python:
            print("Runtime python")
            for entry in runtime_python:
                if isinstance(entry, dict):
                    print(f"- {entry.get('name')} {entry.get('version')}")
        runtime_system = payload.get("runtime_system")
        if isinstance(runtime_system, list) and runtime_system:
            print("Runtime system")
            for entry in runtime_system:
                if isinstance(entry, dict):
                    print(f"- {entry.get('name')} {entry.get('version')}")
        return

    if cmd == "verify":
        if payload.get("status") == "ok":
            print("Dependencies verified.")
            return
        print("Dependency verification failed.")
        for issue in payload.get("package_issues", []):
            if isinstance(issue, dict):
                print(f"- {issue.get('name')}: {issue.get('message')}")
        for issue in payload.get("runtime_issues", []):
            if isinstance(issue, dict):
                print(f"- {issue.get('name')}: {issue.get('message')}")
        return

    if cmd == "audit":
        summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
        print("Dependency audit")
        print(f"vulnerabilities: {summary.get('vulnerability_count', 0)}")
        print(f"trust warnings: {summary.get('trust_warning_count', 0)}")
        if payload.get("status") == "fail":
            print("Audit failed. Run with --json for details.")
        return

    if cmd == "add":
        print(f"Added {payload.get('dependency_type')} dependency: {payload.get('added')}")
        return
    if cmd == "remove":
        if payload.get("status") == "ok":
            print(f"Removed {payload.get('dependency_type')} dependency: {payload.get('removed')}")
        else:
            print(payload.get("reason") or "Dependency was not found.")
        return

    if cmd == "clean":
        removed = payload.get("removed")
        if isinstance(removed, list) and removed:
            print("Removed:")
            for path in removed:
                print(f"- {path}")
        else:
            print("Nothing to clean.")
        return

    if cmd == "update":
        print(f"Updated packages: {payload.get('updated_count', 0)}")

    print(f"{cmd} status: {payload.get('status')}")


__all__ = [
    "DEPENDENCY_MANAGEMENT_CAPABILITY",
    "run_dependency_root",
    "run_dependency_subcommand",
]
