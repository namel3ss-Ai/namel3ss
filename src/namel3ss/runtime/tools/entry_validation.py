from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import re

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message


BUILTIN_TOOL_PACK_PREFIX = "namel3ss.tool_packs"
_NODE_ALLOWED_EXTENSIONS = {"js", "cjs", "mjs", "ts"}
_NODE_FUNCTION_RE = re.compile(r"^[A-Za-z_$][A-Za-z0-9_$]*$")


def validate_python_tool_entry(
    entry: str,
    tool_name: str,
    *,
    line: int | None,
    column: int | None,
    allow_external: bool = False,
) -> tuple[str, str]:
    if ":" not in entry:
        raise Namel3ssError(
            build_guidance_message(
                what=f'Tool "{tool_name}" entry must be "module:function".',
                why="The entry string is missing a ':' separator.",
                fix='Bind the tool using `n3 tools bind "tool_name" --entry "tools.my_tool:run"`.',
                example=_tool_example(tool_name, entry),
            ),
            line=line,
            column=column,
        )
    module_path, function_name = entry.split(":", 1)
    module_path = module_path.strip()
    function_name = function_name.strip()
    if not module_path or not function_name:
        raise Namel3ssError(
            build_guidance_message(
                what=f'Tool "{tool_name}" entry must be "module:function".',
                why="The entry string is missing a module or function name.",
                fix='Bind the tool using `n3 tools bind "tool_name" --entry "tools.my_tool:run"`.',
                example=_tool_example(tool_name, entry),
            ),
            line=line,
            column=column,
        )
    if not allow_external and not _module_allowed(module_path):
        raise Namel3ssError(
            build_guidance_message(
                what=f'Tool "{tool_name}" entry must point inside tools/ or built-in packs.',
                why=f"Entry module '{module_path}' is not allowed.",
                fix='Use a module under tools/ or a built-in pack under "namel3ss.tool_packs".',
                example=_tool_example(tool_name, entry),
            ),
            line=line,
            column=column,
        )
    if not _module_segments_valid(module_path):
        raise Namel3ssError(
            build_guidance_message(
                what=f'Tool "{tool_name}" entry has invalid module path.',
                why=f"'{module_path}' is not a valid Python module path.",
                fix="Use dot-separated Python identifiers for the module path.",
                example=_tool_example(tool_name, entry),
            ),
            line=line,
            column=column,
        )
    if not function_name.isidentifier():
        raise Namel3ssError(
            build_guidance_message(
                what=f'Tool "{tool_name}" entry has invalid function name.',
                why=f"'{function_name}' is not a valid Python identifier.",
                fix="Rename the function or update the binding entry to a valid name.",
                example=_tool_example(tool_name, entry),
            ),
            line=line,
            column=column,
        )
    return module_path, function_name


def validate_node_tool_entry(
    entry: str,
    tool_name: str,
    *,
    line: int | None,
    column: int | None,
    allow_external: bool = False,
) -> tuple[str, str]:
    if ":" not in entry:
        raise Namel3ssError(
            build_guidance_message(
                what=f'Tool "{tool_name}" entry must be "module:function".',
                why="The entry string is missing a ':' separator.",
                fix='Bind the tool using `n3 tools bind "tool_name" --entry "tools.my_tool:run"`.',
                example=_node_entry_example(tool_name, entry),
            ),
            line=line,
            column=column,
        )
    module_path, function_name = entry.split(":", 1)
    module_path = module_path.strip()
    function_name = function_name.strip()
    if not module_path or not function_name:
        raise Namel3ssError(
            build_guidance_message(
                what=f'Tool "{tool_name}" entry must be "module:function".',
                why="The entry string is missing a module or function name.",
                fix='Bind the tool using `n3 tools bind "tool_name" --entry "tools.my_tool:run"`.',
                example=_node_entry_example(tool_name, entry),
            ),
            line=line,
            column=column,
        )
    if not allow_external and not _node_module_allowed(module_path):
        raise Namel3ssError(
            build_guidance_message(
                what=f'Tool "{tool_name}" entry must point inside tools/.',
                why=f"Entry module '{module_path}' is not allowed.",
                fix='Use a module under tools/ in your project.',
                example=_node_entry_example(tool_name, entry),
            ),
            line=line,
            column=column,
        )
    if not _node_module_segments_valid(module_path):
        raise Namel3ssError(
            build_guidance_message(
                what=f'Tool "{tool_name}" entry has invalid module path.',
                why=f"'{module_path}' is not a valid module path.",
                fix="Use dot-separated or tools/ paths with safe characters.",
                example=_node_entry_example(tool_name, entry),
            ),
            line=line,
            column=column,
        )
    if not _node_function_name_valid(function_name):
        raise Namel3ssError(
            build_guidance_message(
                what=f'Tool "{tool_name}" entry has invalid function name.',
                why=f"'{function_name}' is not a valid function identifier.",
                fix="Rename the function or update the binding entry to a valid name.",
                example=_node_entry_example(tool_name, entry),
            ),
            line=line,
            column=column,
        )
    return module_path, function_name


def validate_python_tool_entry_exists(
    entry: str,
    tool_name: str,
    *,
    app_root: Path,
    line: int | None,
    column: int | None,
) -> tuple[str, str]:
    module_path, function_name = validate_python_tool_entry(entry, tool_name, line=line, column=column)
    if os.getenv("N3_EXECUTABLE_SPEC") == "1" and (module_path == "tools" or module_path.startswith("tools.")):
        return module_path, function_name
    if module_path == "tools" or module_path.startswith("tools."):
        rel_parts = module_path.split(".")[1:]
        module_file = app_root / "tools"
        if rel_parts:
            module_file = module_file.joinpath(*rel_parts)
        if module_file.with_suffix(".py").exists():
            return module_path, function_name
        if (module_file / "__init__.py").exists():
            return module_path, function_name
        raise Namel3ssError(
            build_guidance_message(
                what=f'Tool "{tool_name}" entry module was not found (missing_tool).',
                why=f"Expected a module at {module_file.with_suffix('.py')} or {module_file / '__init__.py'}.",
                fix="Create the module file or update the binding entry.",
                example=_tool_example(tool_name, entry),
            ),
            line=line,
            column=column,
        )
    spec = importlib.util.find_spec(module_path)
    if spec is None:
        raise Namel3ssError(
            build_guidance_message(
                what=f'Tool "{tool_name}" entry module was not found (missing_tool).',
                why=f"Python could not resolve '{module_path}'.",
                fix="Install the package or update the binding entry.",
                example=_tool_example(tool_name, entry),
            ),
            line=line,
            column=column,
        )
    return module_path, function_name


def _module_allowed(module_path: str) -> bool:
    if module_path == "tools" or module_path.startswith("tools."):
        return True
    if module_path == BUILTIN_TOOL_PACK_PREFIX or module_path.startswith(f"{BUILTIN_TOOL_PACK_PREFIX}."):
        return True
    return False


def _module_segments_valid(module_path: str) -> bool:
    segments = module_path.split(".")
    return all(segment.isidentifier() for segment in segments)


def _tool_example(tool_name: str, entry: str | None) -> str:
    entry_value = entry or "tools.my_tool:run"
    return (
        "tools:\n"
        f'  "{tool_name}":\n'
        '    kind: "python"\n'
        f'    entry: "{entry_value}"'
    )


def _normalize_node_module_path(module_path: str) -> str:
    return module_path.replace("\\", "/")


def _node_module_allowed(module_path: str) -> bool:
    normalized = _normalize_node_module_path(module_path)
    return normalized == "tools" or normalized.startswith("tools/") or normalized.startswith("tools.")


def _node_module_segments_valid(module_path: str) -> bool:
    normalized = _normalize_node_module_path(module_path)
    if "/" in normalized:
        parts = normalized.split("/")
        if any(part in {"", ".", ".."} for part in parts):
            return False
        for part in parts[:-1]:
            if not _node_segment_valid(part):
                return False
        return _node_last_segment_valid(parts[-1])
    segments = module_path.split(".")
    if any(not segment for segment in segments):
        return False
    return all(_node_segment_valid(segment) for segment in segments)


def _node_segment_valid(segment: str) -> bool:
    return bool(_NODE_FUNCTION_RE.match(segment))


def _node_last_segment_valid(segment: str) -> bool:
    if "." not in segment:
        return _node_segment_valid(segment)
    base, ext = segment.rsplit(".", 1)
    if not base or not _node_segment_valid(base):
        return False
    return ext in _NODE_ALLOWED_EXTENSIONS


def _node_function_name_valid(name: str) -> bool:
    return bool(_NODE_FUNCTION_RE.match(name))


def _node_entry_example(tool_name: str, entry: str | None) -> str:
    entry_value = entry or "tools.my_tool:run"
    return (
        "tools:\n"
        f'  "{tool_name}":\n'
        '    kind: "node"\n'
        f'    entry: "{entry_value}"'
    )


__all__ = [
    "BUILTIN_TOOL_PACK_PREFIX",
    "validate_node_tool_entry",
    "validate_python_tool_entry",
    "validate_python_tool_entry_exists",
]
