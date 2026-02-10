from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable
import re

from namel3ss.ast.ui import layout_nodes as ast
from namel3ss.errors.base import Namel3ssError


_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*$")
_STATE_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*$")


def parse_form_node(
    parser: Any,
    line: Any,
    *,
    header: str,
    ancestor_kinds: tuple[str, ...],
    drawer_triggers: tuple[str, ...],
    indent_width: int,
) -> ast.FormNode:
    name = require_name(header[len("form ") :].strip(), line=line.line, column=line.column, context="form name")
    parser._advance()
    options = {"wizard": False, "sections": []}

    def parse_option(entry: Any) -> bool:
        if entry.text == "wizard":
            options["wizard"] = True
            parser._advance()
            return True
        if entry.text.startswith("section "):
            label = entry.text[len("section ") :].strip()
            if not label:
                raise Namel3ssError("section requires a name.", line=entry.line, column=entry.column)
            options["sections"].append(label)
            parser._advance()
            return True
        return False

    children, bindings = parse_block_body(
        parser,
        expected_indent=line.indent + indent_width,
        parent_kind="form",
        ancestor_kinds=ancestor_kinds + ("form",),
        drawer_triggers=drawer_triggers,
        option_parser=parse_option,
    )
    return ast.FormNode(
        name=name,
        wizard=bool(options["wizard"]),
        sections=list(options["sections"]),
        children=children,
        bindings=bindings,
        line=line.line,
        column=line.column,
    )


def parse_table_node(
    parser: Any,
    line: Any,
    *,
    header: str,
    ancestor_kinds: tuple[str, ...],
    drawer_triggers: tuple[str, ...],
    indent_width: int,
) -> ast.TableNode:
    name = require_name(header[len("table ") :].strip(), line=line.line, column=line.column, context="table name")
    parser._advance()
    options = {"reorderable_columns": False, "fixed_header": False}

    def parse_option(entry: Any) -> bool:
        if entry.text in {"reorderable columns", "column reordering"}:
            options["reorderable_columns"] = True
            parser._advance()
            return True
        if entry.text == "fixed header":
            options["fixed_header"] = True
            parser._advance()
            return True
        return False

    children, bindings = parse_block_body(
        parser,
        expected_indent=line.indent + indent_width,
        parent_kind="table",
        ancestor_kinds=ancestor_kinds + ("table",),
        drawer_triggers=drawer_triggers,
        option_parser=parse_option,
    )
    return ast.TableNode(
        name=name,
        reorderable_columns=bool(options["reorderable_columns"]),
        fixed_header=bool(options["fixed_header"]),
        children=children,
        bindings=bindings,
        line=line.line,
        column=line.column,
    )


def parse_card_node(
    parser: Any,
    line: Any,
    *,
    header: str,
    ancestor_kinds: tuple[str, ...],
    drawer_triggers: tuple[str, ...],
    indent_width: int,
) -> ast.CardNode:
    name = require_name(header[len("card ") :].strip(), line=line.line, column=line.column, context="card name")
    parser._advance()
    options = {"expandable": False, "collapsed": False}

    def parse_option(entry: Any) -> bool:
        if entry.text == "expandable":
            options["expandable"] = True
            parser._advance()
            return True
        if entry.text in {"collapsed", "collapsed by default"}:
            options["collapsed"] = True
            parser._advance()
            return True
        return False

    children, bindings = parse_block_body(
        parser,
        expected_indent=line.indent + indent_width,
        parent_kind="card",
        ancestor_kinds=ancestor_kinds + ("card",),
        drawer_triggers=drawer_triggers,
        option_parser=parse_option,
    )
    return ast.CardNode(
        name=name,
        expandable=bool(options["expandable"]),
        collapsed=bool(options["collapsed"]),
        children=children,
        bindings=bindings,
        line=line.line,
        column=line.column,
    )


def parse_tabs_node(
    parser: Any,
    line: Any,
    *,
    header: str,
    ancestor_kinds: tuple[str, ...],
    drawer_triggers: tuple[str, ...],
    indent_width: int,
) -> ast.NavigationTabsNode:
    name = require_name(header[len("tabs ") :].strip(), line=line.line, column=line.column, context="tabs name")
    parser._advance()
    options = {"dynamic_from_state": None}

    def parse_option(entry: Any) -> bool:
        prefix = "dynamic tabs from "
        if not entry.text.startswith(prefix):
            return False
        state_path = parse_state_reference(
            parser,
            entry.text[len(prefix) :].strip(),
            line=entry,
            context="dynamic tabs binding",
        )
        options["dynamic_from_state"] = state_path
        parser._advance()
        return True

    children, bindings = parse_block_body(
        parser,
        expected_indent=line.indent + indent_width,
        parent_kind="tabs",
        ancestor_kinds=ancestor_kinds + ("tabs",),
        drawer_triggers=drawer_triggers,
        option_parser=parse_option,
    )
    return ast.NavigationTabsNode(
        name=name,
        dynamic_from_state=options["dynamic_from_state"],
        children=children,
        bindings=bindings,
        line=line.line,
        column=line.column,
    )


def parse_media_node(
    parser: Any,
    line: Any,
    *,
    header: str,
    ancestor_kinds: tuple[str, ...],
    drawer_triggers: tuple[str, ...],
    indent_width: int,
) -> ast.MediaNode:
    name = require_name(header[len("media ") :].strip(), line=line.line, column=line.column, context="media name")
    parser._advance()
    options = {"inline_crop": False, "annotation": False}

    def parse_option(entry: Any) -> bool:
        if entry.text == "inline crop":
            options["inline_crop"] = True
            parser._advance()
            return True
        if entry.text == "annotation":
            options["annotation"] = True
            parser._advance()
            return True
        return False

    children, bindings = parse_block_body(
        parser,
        expected_indent=line.indent + indent_width,
        parent_kind="media",
        ancestor_kinds=ancestor_kinds + ("media",),
        drawer_triggers=drawer_triggers,
        option_parser=parse_option,
    )
    return ast.MediaNode(
        name=name,
        inline_crop=bool(options["inline_crop"]),
        annotation=bool(options["annotation"]),
        children=children,
        bindings=bindings,
        line=line.line,
        column=line.column,
    )


def parse_block_body(
    parser: Any,
    *,
    expected_indent: int,
    parent_kind: str,
    ancestor_kinds: tuple[str, ...],
    drawer_triggers: tuple[str, ...],
    option_parser: Callable[[Any], bool] | None = None,
) -> tuple[list[ast.LayoutNode], ast.InteractionBindings]:
    children: list[ast.LayoutNode] = []
    sticky_positions: set[str] = set()
    binding_values = empty_binding_values()
    while not parser._at_end():
        line = parser._current()
        if line.indent < expected_indent:
            break
        if line.indent > expected_indent:
            raise Namel3ssError("Unexpected indentation level.", line=line.line, column=line.column)
        if parse_binding_line(parser, line, binding_values):
            parser._advance()
            continue
        if option_parser is not None and option_parser(line):
            continue
        if line.text.endswith(":"):
            child = parser._parse_node(
                parent_kind=parent_kind,
                ancestor_kinds=ancestor_kinds,
                drawer_triggers=drawer_triggers,
            )
        else:
            child = ast.LiteralItemNode(text=line.text, line=line.line, column=line.column)
            parser._advance()
        check_sticky_conflict(
            sticky_positions=sticky_positions,
            node=child,
            line=getattr(child, "line", None),
            column=getattr(child, "column", None),
        )
        children.append(child)
    return children, build_bindings(binding_values)


def parse_state_block(parser: Any, line: Any, *, indent_width: int) -> None:
    parser._advance()
    expected_indent = line.indent + indent_width
    found = False
    while not parser._at_end():
        entry = parser._current()
        if entry.indent < expected_indent:
            break
        if entry.indent > expected_indent:
            raise Namel3ssError("Unexpected indentation level.", line=entry.line, column=entry.column)
        if entry.text.endswith(":"):
            raise Namel3ssError("state entries must be plain paths.", line=entry.line, column=entry.column)
        path = normalize_state_path(entry.text, line=entry.line, column=entry.column)
        if path in parser._declared_state_set:
            raise Namel3ssError(f'state "{path}" is already declared.', line=entry.line, column=entry.column)
        parser._declared_states.append(ast.StateDefinitionNode(path=path, line=entry.line, column=entry.column))
        parser._declared_state_set.add(path)
        found = True
        parser._advance()
    if not found:
        raise Namel3ssError("state block must include at least one path.", line=line.line, column=line.column)


def parse_binding_line(parser: Any, line: Any, values: dict[str, str | None]) -> bool:
    if line.text.startswith("on click "):
        action = line.text[len("on click ") :].strip()
        if not action:
            raise Namel3ssError("on click requires an action id.", line=line.line, column=line.column)
        set_binding(values, "on_click", action, line=line)
        parser._note_feature("on click", line)
        return True
    if line.text.startswith("keyboard shortcut "):
        combo = line.text[len("keyboard shortcut ") :].strip()
        if not combo:
            raise Namel3ssError("keyboard shortcut requires a key combo.", line=line.line, column=line.column)
        set_binding(values, "keyboard_shortcut", combo, line=line)
        parser._note_feature("keyboard shortcut", line)
        return True
    if line.text.startswith("selected item is "):
        state_path = parse_state_reference(
            parser,
            line.text[len("selected item is ") :].strip(),
            line=line,
            context="selected item binding",
        )
        set_binding(values, "selected_item", state_path, line=line)
        parser._note_feature("selected item", line)
        return True
    return False


def parse_state_reference(parser: Any, value: str, *, line: Any, context: str) -> str:
    if not value.startswith("state."):
        raise Namel3ssError(f"{context} must reference state.<path>.", line=line.line, column=line.column)
    path = normalize_state_path(value, line=line.line, column=line.column)
    parser._state_uses.append(_StateUse(path=path, line=line.line, column=line.column))
    return path


@dataclass(frozen=True)
class _StateUse:
    path: str
    line: int
    column: int


def validate_state_references(parser: Any) -> None:
    for use in sorted(parser._state_uses, key=lambda entry: (entry.line, entry.column, entry.path)):
        if use.path in parser._declared_state_set:
            continue
        raise Namel3ssError(
            f'Undefined state reference "state.{use.path}". Declare it in a state: block.',
            line=use.line,
            column=use.column,
        )


def validate_capability(parser: Any, *, required_capability: str) -> None:
    if not parser._feature_uses:
        return
    if parser._studio_mode:
        return
    if required_capability in parser._capabilities:
        return
    first = sorted(parser._feature_uses, key=lambda entry: (entry.line, entry.column, entry.feature))[0]
    raise Namel3ssError(
        f'Feature "{first.feature}" requires capability "{required_capability}" or Studio mode.',
        line=first.line,
        column=first.column,
    )


def normalize_state_path(value: str, *, line: int, column: int) -> str:
    raw = value.strip()
    if raw.startswith("state."):
        raw = raw[len("state.") :]
    if not _STATE_RE.fullmatch(raw):
        raise Namel3ssError("State path must match state.<name>[.<name>...].", line=line, column=column)
    return raw


def require_name(name: str, *, line: int, column: int, context: str) -> str:
    if not _NAME_RE.fullmatch(name):
        raise Namel3ssError(f"{context} must be an identifier.", line=line, column=column)
    return name


def empty_binding_values() -> dict[str, str | None]:
    return {
        "on_click": None,
        "keyboard_shortcut": None,
        "selected_item": None,
    }


def set_binding(values: dict[str, str | None], key: str, value: str, *, line: Any) -> None:
    if values[key] is not None:
        raise Namel3ssError(f"{key.replace('_', ' ')} is already declared.", line=line.line, column=line.column)
    values[key] = value


def build_bindings(values: dict[str, str | None]) -> ast.InteractionBindings:
    return ast.InteractionBindings(
        on_click=values["on_click"],
        keyboard_shortcut=values["keyboard_shortcut"],
        selected_item=values["selected_item"],
    )


def check_sticky_conflict(
    *,
    sticky_positions: set[str],
    node: ast.LayoutNode,
    line: int | None,
    column: int | None,
) -> None:
    if not isinstance(node, ast.StickyNode):
        return
    if node.position in sticky_positions:
        raise Namel3ssError(
            f'Conflicting sticky position "{node.position}" in the same container.',
            line=line,
            column=column,
        )
    sticky_positions.add(node.position)


__all__ = [
    "build_bindings",
    "check_sticky_conflict",
    "empty_binding_values",
    "parse_binding_line",
    "parse_block_body",
    "parse_card_node",
    "parse_form_node",
    "parse_media_node",
    "parse_state_block",
    "parse_state_reference",
    "parse_table_node",
    "parse_tabs_node",
    "require_name",
    "validate_capability",
    "validate_state_references",
]
