from __future__ import annotations

from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.tools.bindings_yaml import ToolBinding, parse_bindings_yaml, render_bindings_yaml
from namel3ss.utils.slugify import slugify_tool_name

BINDINGS_DIR = ".namel3ss"
BINDINGS_FILE = "tools.yaml"


def bindings_path(app_root: Path) -> Path:
    return app_root / BINDINGS_DIR / BINDINGS_FILE


def load_tool_bindings(app_root: Path) -> dict[str, ToolBinding]:
    path = bindings_path(app_root)
    if not path.exists():
        return {}
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as err:
        raise Namel3ssError(
            build_guidance_message(
                what="Unable to read tool bindings.",
                why=str(err),
                fix=f"Ensure {path.as_posix()} is readable.",
                example=_bindings_example("get data from a web address"),
            )
        ) from err
    return parse_bindings_yaml(text, path)


def write_tool_bindings(app_root: Path, bindings: dict[str, ToolBinding]) -> Path:
    path = bindings_path(app_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    content = render_bindings_yaml(bindings)
    path.write_text(content, encoding="utf-8")
    return path


def resolve_tool_binding(app_root: Path, tool_name: str, *, line: int | None, column: int | None) -> ToolBinding:
    bindings = load_tool_bindings(app_root)
    binding = bindings.get(tool_name)
    if not binding:
        slug = slugify_tool_name(tool_name)
        raise Namel3ssError(
            build_guidance_message(
                what=f'Tool "{tool_name}" is not bound to a python entry.',
                why="Tool declarations no longer include module paths; bindings live in .namel3ss/tools.yaml.",
                fix=(
                    "Check bindings with `n3 tools status`, then run "
                    f'`n3 tools bind "{tool_name}" --entry "tools.{slug}:run"` '
                    "or `n3 tools bind --from-app`."
                ),
                example=_bindings_example(tool_name),
            ),
            line=line,
            column=column,
        )
    return binding


def _bindings_example(tool_name: str) -> str:
    return (
        "tools:\n"
        f'  "{tool_name}":\n'
        '    kind: "python"\n'
        '    entry: "tools.my_tool:run"'
    )


__all__ = ["bindings_path", "load_tool_bindings", "resolve_tool_binding", "write_tool_bindings"]
