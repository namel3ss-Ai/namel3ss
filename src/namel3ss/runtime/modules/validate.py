from __future__ import annotations

from pathlib import Path

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message


def validate_module_program(program: ast.Program, *, path: Path) -> None:
    if program.app_theme_line is not None:
        raise Namel3ssError(
            build_guidance_message(
                what="App declaration is not allowed in modules.",
                why="Modules only declare reusable items.",
                fix="Move the app declaration to app.ai.",
                example='app:\n  theme is "system"',
            )
        )
    if program.identity is not None:
        raise Namel3ssError(
            build_guidance_message(
                what="Identity is not allowed in modules.",
                why="Identity belongs in app.ai.",
                fix="Move the identity block to app.ai.",
                example='identity "user":',
            )
        )
    if program.capsule is not None:
        raise Namel3ssError(
            build_guidance_message(
                what="Capsule declaration is not allowed in modules.",
                why="Modules are single files without capsule blocks.",
                fix="Remove the capsule declaration.",
                example='use module "modules/common.ai" as common',
            )
        )
    if program.uses:
        raise Namel3ssError(
            build_guidance_message(
                what="Module files cannot import other modules.",
                why="Reuse must be declared in app.ai.",
                fix="Move use module statements to app.ai.",
                example='use module "modules/common.ai" as common',
            )
        )
    if program.flows:
        raise Namel3ssError(
            build_guidance_message(
                what="Flows are not allowed in modules.",
                why="Modules only define reusable items.",
                fix="Move the flow to app.ai or remove it.",
                example='flow "run":',
            )
        )
    if program.ais or program.agents:
        raise Namel3ssError(
            build_guidance_message(
                what="AI and agent declarations are not allowed in modules.",
                why="Modules only define functions, records, tools, and pages.",
                fix="Move AI and agent declarations to app.ai.",
                example='ai "assistant":',
            )
        )

    _ensure_unique(program.functions, "function", path)
    _ensure_unique(program.records, "record", path)
    _ensure_unique(program.tools, "tool", path)
    _ensure_unique(program.pages, "page", path)
    _ensure_unique(getattr(program, "ui_packs", []), "ui_pack", path)


def _ensure_unique(items, kind: str, path: Path) -> None:
    seen: dict[str, ast.Node] = {}
    for item in items:
        name = getattr(item, "name", None)
        if not isinstance(name, str) or not name:
            raise Namel3ssError(
                build_guidance_message(
                    what=f"A {kind} is missing a name.",
                    why="All declarations must have names.",
                    fix=f"Add a name to the {kind}.",
                    example=f'{kind} "name":',
                ),
                details={"file": path.as_posix()},
            )
        if name in seen:
            dup = seen[name]
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Duplicate {kind} name '{name}'.",
                    why=f"Module files cannot declare the same {kind} twice.",
                    fix=f"Keep a single {kind} named {name}.",
                    example=f'{kind} "{name}":',
                ),
                line=getattr(item, "line", None),
                column=getattr(item, "column", None),
                details={"file": path.as_posix()},
            )
        seen[name] = item


__all__ = ["validate_module_program"]
