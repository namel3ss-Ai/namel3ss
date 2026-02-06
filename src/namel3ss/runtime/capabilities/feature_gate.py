from __future__ import annotations

from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.lang.capabilities import normalize_builtin_capability
from namel3ss.module_loader import load_project


def require_app_capability(
    app_path: str | Path,
    capability: str,
    *,
    source_override: str | None = None,
) -> None:
    app_file = Path(app_path).resolve()
    normalized = normalize_builtin_capability(capability)
    if normalized is None:
        normalized = str(capability or "").strip().lower()
    overrides = {app_file: source_override} if isinstance(source_override, str) else None
    project = load_project(app_file, source_overrides=overrides)
    declared = set(_normalize_capabilities(getattr(project.program, "capabilities", ())))
    if normalized in declared:
        return
    raise Namel3ssError(_missing_capability_message(normalized))


def _normalize_capabilities(values: object) -> tuple[str, ...]:
    if not isinstance(values, (list, tuple)):
        return ()
    normalized: list[str] = []
    for value in values:
        token = normalize_builtin_capability(value if isinstance(value, str) else None)
        if token and token not in normalized:
            normalized.append(token)
    return tuple(normalized)


def _missing_capability_message(name: str) -> str:
    return build_guidance_message(
        what=f'Capability "{name}" is required.',
        why="This feature is opt-in and disabled by default.",
        fix=f"Add the capability to the app and retry.",
        example=f'spec is "1.0"\n\ncapabilities:\n  {name}',
    )


__all__ = ["require_app_capability"]
