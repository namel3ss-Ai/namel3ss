from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


CANONICAL_TYPES = {"text", "number", "boolean", "json", "list", "map"}

LEGACY_TYPE_ALIASES = {
    "string": "text",
    "str": "text",
    "int": "number",
    "integer": "number",
    "bool": "boolean",
}


@dataclass(frozen=True)
class _TypeNode:
    kind: str  # name, generic, union
    name: str | None = None
    args: tuple["_TypeNode", ...] = ()


class _TypeParser:
    def __init__(self, source: str) -> None:
        self.source = source
        self.pos = 0
        self.alias_used = False

    def parse(self) -> _TypeNode:
        node = self._parse_union()
        self._skip_space()
        if self.pos != len(self.source):
            raise ValueError(f"Unexpected token at position {self.pos}")
        return node

    def _parse_union(self) -> _TypeNode:
        options = [self._parse_generic_or_name()]
        while True:
            self._skip_space()
            if not self._match("|"):
                break
            options.append(self._parse_generic_or_name())
        if len(options) == 1:
            return options[0]
        return _TypeNode(kind="union", args=tuple(options))

    def _parse_generic_or_name(self) -> _TypeNode:
        self._skip_space()
        name = self._parse_name()
        self._skip_space()
        if not self._match("<"):
            return _TypeNode(kind="name", name=name)
        args = [self._parse_union()]
        while True:
            self._skip_space()
            if self._match(","):
                args.append(self._parse_union())
                continue
            break
        self._skip_space()
        if not self._match(">"):
            raise ValueError("Missing closing '>' in generic type")
        return _TypeNode(kind="generic", name=name, args=tuple(args))

    def _parse_name(self) -> str:
        self._skip_space()
        start = self.pos
        while self.pos < len(self.source):
            ch = self.source[self.pos]
            if ch.isalnum() or ch in {"_", "."}:
                self.pos += 1
                continue
            break
        if self.pos == start:
            raise ValueError(f"Expected type name at position {self.pos}")
        raw = self.source[start:self.pos]
        canonical, was_alias = canonicalize_type_name(raw)
        if was_alias:
            self.alias_used = True
        return canonical

    def _skip_space(self) -> None:
        while self.pos < len(self.source) and self.source[self.pos].isspace():
            self.pos += 1

    def _match(self, token: str) -> bool:
        if self.source.startswith(token, self.pos):
            self.pos += len(token)
            return True
        return False


def canonicalize_type_name(raw: str) -> Tuple[str, bool]:
    """
    Normalize a raw type name to its canonical form.

    Returns a pair of canonical_type and was_alias.
    """
    lowered = str(raw).strip()
    if lowered in CANONICAL_TYPES:
        return lowered, False
    mapped = LEGACY_TYPE_ALIASES.get(lowered)
    if mapped:
        return mapped, True
    return lowered, False


def normalize_type_name(raw: str) -> Tuple[str, bool]:
    return canonicalize_type_name(raw)


def normalize_type_expression(raw: str) -> tuple[str, bool]:
    text = str(raw or "").strip()
    if not text:
        raise ValueError("Type expression is empty")
    parser = _TypeParser(text)
    node = parser.parse()
    return render_type_expression(node), parser.alias_used


def is_supported_type_name(raw: str) -> bool:
    try:
        parser = _TypeParser(str(raw or "").strip())
        node = parser.parse()
        return _is_supported_node(node)
    except Exception:
        return False


def split_union_members(raw: str) -> tuple[str, ...]:
    normalized, _ = normalize_type_expression(raw)
    parts: list[str] = []
    depth = 0
    start = 0
    for idx, ch in enumerate(normalized):
        if ch == "<":
            depth += 1
        elif ch == ">":
            depth -= 1
        elif ch == "|" and depth == 0:
            parts.append(normalized[start:idx].strip())
            start = idx + 1
    parts.append(normalized[start:].strip())
    return tuple(part for part in parts if part)


def render_type_expression(node: _TypeNode) -> str:
    if node.kind == "name":
        return str(node.name or "")
    if node.kind == "generic":
        args = ", ".join(render_type_expression(item) for item in node.args)
        return f"{node.name}<{args}>"
    if node.kind == "union":
        return " | ".join(render_type_expression(item) for item in node.args)
    raise ValueError(f"Unknown type node kind '{node.kind}'")


def _is_supported_node(node: _TypeNode) -> bool:
    if node.kind == "name":
        if node.name in CANONICAL_TYPES:
            return True
        return node.name == "null"
    if node.kind == "generic":
        if node.name == "list":
            return len(node.args) == 1 and _is_supported_node(node.args[0])
        if node.name == "map":
            return len(node.args) == 2 and all(_is_supported_node(arg) for arg in node.args)
        return False
    if node.kind == "union":
        return len(node.args) >= 2 and all(_is_supported_node(arg) for arg in node.args)
    return False


__all__ = [
    "CANONICAL_TYPES",
    "LEGACY_TYPE_ALIASES",
    "canonicalize_type_name",
    "is_supported_type_name",
    "normalize_type_expression",
    "normalize_type_name",
    "render_type_expression",
    "split_union_members",
]
