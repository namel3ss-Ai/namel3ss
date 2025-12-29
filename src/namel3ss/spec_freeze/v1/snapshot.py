from __future__ import annotations

import inspect
import re
import typing
from types import UnionType
from typing import Union, get_args, get_origin, get_type_hints

from namel3ss.ast import expressions as ast_expressions
from namel3ss.ast import nodes as ast_nodes
from namel3ss.ast import statements as ast_statements
from namel3ss.ast.base import Node
from namel3ss.ast.program import Program
from namel3ss.lexer.tokens import KEYWORDS
from namel3ss.types import CANONICAL_TYPES, TYPE_ALIASES


_CAMEL_BOUNDARY = re.compile(r"([a-z0-9])([A-Z])")


def build_snapshot() -> dict:
    """Build a stable snapshot of the current language surface."""
    return {
        "keywords": _sorted_keywords(),
        "decl_forms": _decl_forms(),
        "statement_forms": _statement_forms(),
        "expression_forms": _expression_forms(),
        "types": {
            "canonical": sorted(CANONICAL_TYPES),
            "aliases": _sorted_aliases(),
        },
    }


def _sorted_keywords() -> list[str]:
    return sorted(KEYWORDS.keys())


def _decl_forms() -> list[str]:
    forms: set[str] = set()
    hint_globals = dict(vars(ast_nodes))
    hint_globals.update(vars(typing))
    type_hints = get_type_hints(Program, globalns=hint_globals, localns=hint_globals)
    for name, hint in type_hints.items():
        for node_type in _extract_node_types(hint):
            forms.add(_decl_form_name(node_type))
        if name == "spec_version":
            forms.add("spec")
        if name == "app_theme":
            forms.add("app")
    return sorted(forms)


def _statement_forms() -> list[str]:
    return _class_forms(ast_statements, ast_statements.Statement, trim_suffix="Stmt")


def _expression_forms() -> list[str]:
    return _class_forms(ast_expressions, ast_expressions.Expression)


def _class_forms(module, base_type, *, trim_suffix: str | None = None) -> list[str]:
    names = []
    for _, cls in inspect.getmembers(module, inspect.isclass):
        if cls is base_type:
            continue
        if cls.__module__ != module.__name__:
            continue
        if not issubclass(cls, base_type):
            continue
        class_name = cls.__name__
        if trim_suffix and class_name.endswith(trim_suffix):
            class_name = class_name[: -len(trim_suffix)]
        names.append(_camel_to_snake(class_name))
    return sorted(set(names))


def _decl_form_name(node_type: type[Node]) -> str:
    name = node_type.__name__
    if name.endswith("Decl"):
        name = name[: -len("Decl")]
    return _camel_to_snake(name)


def _camel_to_snake(value: str) -> str:
    return _CAMEL_BOUNDARY.sub(r"\1_\2", value).lower()


def _extract_node_types(hint) -> list[type[Node]]:
    origin = get_origin(hint)
    if origin in {list, tuple}:
        args = get_args(hint)
        return _extract_node_types(args[0]) if args else []
    if origin is dict:
        args = get_args(hint)
        return _extract_node_types(args[1]) if len(args) > 1 else []
    if origin in {Union, UnionType}:
        types: list[type[Node]] = []
        for arg in get_args(hint):
            if arg is type(None):
                continue
            types.extend(_extract_node_types(arg))
        return types
    if origin is None:
        if inspect.isclass(hint) and issubclass(hint, Node):
            return [hint]
        return []
    return []


def _sorted_aliases() -> list[dict]:
    return [
        {"alias": alias, "canonical": canonical}
        for alias, canonical in sorted(TYPE_ALIASES.items(), key=lambda item: item[0])
    ]


__all__ = ["build_snapshot"]
