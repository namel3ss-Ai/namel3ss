from __future__ import annotations

import os
from pathlib import Path
from namel3ss.cli.aliases import canonical_command
from namel3ss.errors.base import Namel3ssError

def allow_aliases_from_flags(flags: list[str]) -> bool:
    env_disallow = os.getenv("N3_NO_LEGACY_TYPE_ALIASES")
    allow_aliases = True
    if env_disallow and env_disallow.lower() in {"1", "true", "yes"}:
        allow_aliases = False
    if "--no-legacy-type-aliases" in flags:
        allow_aliases = False
    if "--allow-legacy-type-aliases" in flags:
        allow_aliases = True
    return allow_aliases

def extract_app_override(remainder: list[str], app_override: str | None) -> tuple[str | None, list[str]]:
    if not remainder:
        return app_override, remainder
    command = canonical_command(remainder[0])
    if command not in {"check", "fmt", "lint", "studio"}:
        return app_override, remainder
    tail = remainder[1:]
    for idx, item in enumerate(tail):
        if item.endswith(".ai"):
            if app_override is not None:
                raise Namel3ssError("App path was provided twice. Use either an explicit app path or --app.")
            new_tail = tail[:idx] + tail[idx + 1 :]
            return item, [remainder[0], *new_tail]
    return app_override, remainder

def resolve_explicit_path(app_override: str, project_root: str | None) -> Path:
    path = Path(app_override)
    if project_root and not path.is_absolute():
        path = Path(project_root) / path
    return path.resolve()
