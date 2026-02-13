from __future__ import annotations

from pathlib import Path
import sys
from typing import Callable

from namel3ss.cli.workspace.resolution_contract import WorkspaceResolutionContract


def build_workspace_resolution_warning(contract: WorkspaceResolutionContract) -> str:
    if not contract.warning_required or contract.selected_app_path is None:
        return ""
    selected = _display_path(contract.search_root, contract.selected_app_path)
    alternatives = [
        _display_path(contract.search_root, path)
        for path in contract.alternative_app_paths
    ]
    alternatives_text = ", ".join(alternatives) if alternatives else "none"
    return (
        "Workspace contains multiple app roots.\n"
        f"Selected: {selected}\n"
        f"Alternatives: {alternatives_text}\n"
        "Use --app <path> to target a specific app."
    )


def emit_workspace_resolution_warning(
    contract: WorkspaceResolutionContract,
    *,
    printer: Callable[[str], None] | None = None,
) -> None:
    message = build_workspace_resolution_warning(contract)
    if not message:
        return
    sink = printer or _stderr_printer
    sink(message)


def _display_path(root: Path, value: Path) -> str:
    try:
        return value.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return value.resolve().as_posix()


def _stderr_printer(message: str) -> None:
    print(message, file=sys.stderr)


__all__ = [
    "build_workspace_resolution_warning",
    "emit_workspace_resolution_warning",
]
