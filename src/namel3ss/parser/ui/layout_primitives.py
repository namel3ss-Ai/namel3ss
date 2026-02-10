from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable

from namel3ss.ast.ui import layout_nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.parser.ui.layout_primitives_components import (
    build_bindings,
    check_sticky_conflict,
    empty_binding_values,
    parse_binding_line,
    parse_block_body,
    parse_card_node,
    parse_form_node,
    parse_media_node,
    parse_state_block,
    parse_table_node,
    parse_tabs_node,
    require_name,
    validate_capability,
    validate_state_references,
)
REQUIRED_CAPABILITY = "ui.custom_layouts"
_INDENT_WIDTH = 2
@dataclass(frozen=True)
class _SourceLine:
    line: int
    indent: int
    column: int
    text: str


@dataclass(frozen=True)
class _FeatureUse:
    feature: str
    line: int
    column: int


def parse_layout_page(
    source: str,
    *,
    capabilities: Iterable[str] | None = None,
    studio_mode: bool = False,
) -> ast.PageNode:
    parser = _LayoutPrimitiveParser(source, capabilities=capabilities, studio_mode=studio_mode)
    return parser.parse()

class _LayoutPrimitiveParser:
    def __init__(
        self,
        source: str,
        *,
        capabilities: Iterable[str] | None = None,
        studio_mode: bool = False,
    ) -> None:
        self._lines = _scan_source(source)
        self._index = 0
        self._declared_states: list[ast.StateDefinitionNode] = []
        self._declared_state_set: set[str] = set()
        self._state_uses: list[object] = []
        self._feature_uses: list[_FeatureUse] = []
        self._capabilities = {str(cap).strip().lower() for cap in capabilities or []}
        self._studio_mode = bool(studio_mode)

    def parse(self) -> ast.PageNode:
        if not self._lines:
            raise Namel3ssError("Expected a page block.", line=1, column=1)
        first = self._current()
        if first.indent != 0:
            raise Namel3ssError("Page block must start at column 1.", line=first.line, column=first.column)
        if not first.text.endswith(":"):
            raise Namel3ssError("Expected ':' after page header.", line=first.line, column=first.column)
        header = first.text[:-1].strip()
        if not header.startswith("page "):
            raise Namel3ssError("Layout blocks must be declared inside a page root.", line=first.line, column=first.column)
        page_name = require_name(header[len("page ") :].strip(), line=first.line, column=first.column, context="page name")
        self._advance()
        children = self._parse_children(
            expected_indent=first.indent + _INDENT_WIDTH,
            parent_kind="page",
            ancestor_kinds=("page",),
            drawer_triggers=(),
        )
        if self._index != len(self._lines):
            line = self._current()
            raise Namel3ssError(
                "Only one page block is allowed in this grammar entry point.",
                line=line.line,
                column=line.column,
            )
        validate_state_references(self)
        validate_capability(self, required_capability=REQUIRED_CAPABILITY)
        return ast.PageNode(
            name=page_name,
            states=list(self._declared_states),
            children=children,
            line=first.line,
            column=first.column,
        )

    def _parse_children(
        self,
        *,
        expected_indent: int,
        parent_kind: str,
        ancestor_kinds: tuple[str, ...],
        drawer_triggers: tuple[str, ...],
    ) -> list[ast.LayoutNode]:
        children: list[ast.LayoutNode] = []
        sticky_positions: set[str] = set()
        while not self._at_end():
            line = self._current()
            if line.indent < expected_indent:
                break
            if line.indent > expected_indent:
                raise Namel3ssError("Unexpected indentation level.", line=line.line, column=line.column)
            if parent_kind == "page" and line.text == "state:":
                parse_state_block(self, line, indent_width=_INDENT_WIDTH)
                continue
            if parent_kind == "page" and not line.text.endswith(":"):
                raise Namel3ssError(
                    "Page children must be block declarations ending with ':'.",
                    line=line.line,
                    column=line.column,
                )
            node = self._parse_node(
                parent_kind=parent_kind,
                ancestor_kinds=ancestor_kinds,
                drawer_triggers=drawer_triggers,
            )
            check_sticky_conflict(
                sticky_positions=sticky_positions,
                node=node,
                line=getattr(node, "line", None),
                column=getattr(node, "column", None),
            )
            children.append(node)
        return children

    def _parse_node(
        self,
        *,
        parent_kind: str,
        ancestor_kinds: tuple[str, ...],
        drawer_triggers: tuple[str, ...],
    ) -> ast.LayoutNode:
        line = self._current()
        if not line.text.endswith(":"):
            text = line.text
            self._advance()
            return ast.LiteralItemNode(text=text, line=line.line, column=line.column)
        header = line.text[:-1].strip()
        if header == "sidebar":
            return self._parse_sidebar(line, ancestor_kinds=ancestor_kinds, drawer_triggers=drawer_triggers)
        if header == "main":
            return self._parse_main(line, ancestor_kinds=ancestor_kinds, drawer_triggers=drawer_triggers)
        if header.startswith("drawer "):
            return self._parse_drawer(line, header=header, ancestor_kinds=ancestor_kinds, drawer_triggers=drawer_triggers)
        if header.startswith("sticky "):
            return self._parse_sticky(line, header=header, ancestor_kinds=ancestor_kinds, drawer_triggers=drawer_triggers)
        if header.startswith("scroll area"):
            return self._parse_scroll_area(line, header=header, ancestor_kinds=ancestor_kinds, drawer_triggers=drawer_triggers)
        if header == "two_pane":
            return self._parse_two_pane(line, ancestor_kinds=ancestor_kinds, drawer_triggers=drawer_triggers)
        if header == "three_pane":
            return self._parse_three_pane(line, ancestor_kinds=ancestor_kinds, drawer_triggers=drawer_triggers)
        if header.startswith("form "):
            return parse_form_node(
                self,
                line,
                header=header,
                ancestor_kinds=ancestor_kinds,
                drawer_triggers=drawer_triggers,
                indent_width=_INDENT_WIDTH,
            )
        if header.startswith("table "):
            return parse_table_node(
                self,
                line,
                header=header,
                ancestor_kinds=ancestor_kinds,
                drawer_triggers=drawer_triggers,
                indent_width=_INDENT_WIDTH,
            )
        if header.startswith("card "):
            return parse_card_node(
                self,
                line,
                header=header,
                ancestor_kinds=ancestor_kinds,
                drawer_triggers=drawer_triggers,
                indent_width=_INDENT_WIDTH,
            )
        if header.startswith("tabs "):
            return parse_tabs_node(
                self,
                line,
                header=header,
                ancestor_kinds=ancestor_kinds,
                drawer_triggers=drawer_triggers,
                indent_width=_INDENT_WIDTH,
            )
        if header.startswith("media "):
            return parse_media_node(
                self,
                line,
                header=header,
                ancestor_kinds=ancestor_kinds,
                drawer_triggers=drawer_triggers,
                indent_width=_INDENT_WIDTH,
            )
        raise Namel3ssError(f'Unknown block "{header}".', line=line.line, column=line.column)

    def _parse_sidebar(
        self,
        line: _SourceLine,
        *,
        ancestor_kinds: tuple[str, ...],
        drawer_triggers: tuple[str, ...],
    ) -> ast.SidebarNode:
        if "sidebar" in ancestor_kinds:
            raise Namel3ssError("Nested sidebar blocks are not allowed.", line=line.line, column=line.column)
        self._note_feature("sidebar", line)
        self._advance()
        children, bindings = parse_block_body(
            self,
            expected_indent=line.indent + _INDENT_WIDTH,
            parent_kind="sidebar",
            ancestor_kinds=ancestor_kinds + ("sidebar",),
            drawer_triggers=drawer_triggers,
        )
        return ast.SidebarNode(children=children, bindings=bindings, line=line.line, column=line.column)

    def _parse_main(
        self,
        line: _SourceLine,
        *,
        ancestor_kinds: tuple[str, ...],
        drawer_triggers: tuple[str, ...],
    ) -> ast.MainNode:
        self._advance()
        children, bindings = parse_block_body(
            self,
            expected_indent=line.indent + _INDENT_WIDTH,
            parent_kind="main",
            ancestor_kinds=ancestor_kinds + ("main",),
            drawer_triggers=drawer_triggers,
        )
        return ast.MainNode(children=children, bindings=bindings, line=line.line, column=line.column)

    def _parse_drawer(
        self,
        line: _SourceLine,
        *,
        header: str,
        ancestor_kinds: tuple[str, ...],
        drawer_triggers: tuple[str, ...],
    ) -> ast.DrawerNode:
        match = re.fullmatch(r"drawer\s+(left|right)(?:\s+trigger\s+([A-Za-z_][A-Za-z0-9_-]*))?", header)
        if match is None:
            raise Namel3ssError(
                "Drawer syntax is: drawer <left|right> trigger <trigger_id>:",
                line=line.line,
                column=line.column,
            )
        trigger_id = match.group(2)
        if not trigger_id:
            raise Namel3ssError("Drawer blocks must declare trigger_id.", line=line.line, column=line.column)
        if trigger_id in drawer_triggers:
            raise Namel3ssError(f'Drawer trigger cycle detected for "{trigger_id}".', line=line.line, column=line.column)
        self._note_feature("drawer", line)
        self._advance()
        children, bindings = parse_block_body(
            self,
            expected_indent=line.indent + _INDENT_WIDTH,
            parent_kind="drawer",
            ancestor_kinds=ancestor_kinds + ("drawer",),
            drawer_triggers=drawer_triggers + (trigger_id,),
        )
        if not children:
            raise Namel3ssError("Drawer blocks must include at least one child.", line=line.line, column=line.column)
        return ast.DrawerNode(
            side=match.group(1),
            trigger_id=trigger_id,
            children=children,
            bindings=bindings,
            line=line.line,
            column=line.column,
        )

    def _parse_sticky(
        self,
        line: _SourceLine,
        *,
        header: str,
        ancestor_kinds: tuple[str, ...],
        drawer_triggers: tuple[str, ...],
    ) -> ast.StickyNode:
        match = re.fullmatch(r"sticky\s+(top|bottom)", header)
        if match is None:
            raise Namel3ssError("Sticky syntax is: sticky <top|bottom>:", line=line.line, column=line.column)
        self._note_feature("sticky", line)
        self._advance()
        children, bindings = parse_block_body(
            self,
            expected_indent=line.indent + _INDENT_WIDTH,
            parent_kind="sticky",
            ancestor_kinds=ancestor_kinds + ("sticky",),
            drawer_triggers=drawer_triggers,
        )
        if not children:
            raise Namel3ssError("Sticky blocks must include at least one child.", line=line.line, column=line.column)
        return ast.StickyNode(
            position=match.group(1),
            children=children,
            bindings=bindings,
            line=line.line,
            column=line.column,
        )

    def _parse_scroll_area(
        self,
        line: _SourceLine,
        *,
        header: str,
        ancestor_kinds: tuple[str, ...],
        drawer_triggers: tuple[str, ...],
    ) -> ast.ScrollAreaNode:
        match = re.fullmatch(r"scroll area(?:\s+axis\s+(vertical|horizontal))?", header)
        if match is None:
            raise Namel3ssError(
                "Scroll area syntax is: scroll area: or scroll area axis <vertical|horizontal>:",
                line=line.line,
                column=line.column,
            )
        self._note_feature("scroll area", line)
        self._advance()
        children, bindings = parse_block_body(
            self,
            expected_indent=line.indent + _INDENT_WIDTH,
            parent_kind="scroll_area",
            ancestor_kinds=ancestor_kinds + ("scroll_area",),
            drawer_triggers=drawer_triggers,
        )
        if not children:
            raise Namel3ssError("Scroll area blocks must include at least one child.", line=line.line, column=line.column)
        return ast.ScrollAreaNode(
            axis=match.group(1) or "vertical",
            children=children,
            bindings=bindings,
            line=line.line,
            column=line.column,
        )

    def _parse_two_pane(
        self,
        line: _SourceLine,
        *,
        ancestor_kinds: tuple[str, ...],
        drawer_triggers: tuple[str, ...],
    ) -> ast.TwoPaneNode:
        self._note_feature("two_pane", line)
        self._advance()
        bindings_data = empty_binding_values()
        primary: list[ast.LayoutNode] | None = None
        secondary: list[ast.LayoutNode] | None = None
        expected_indent = line.indent + _INDENT_WIDTH
        while not self._at_end():
            current = self._current()
            if current.indent < expected_indent:
                break
            if current.indent > expected_indent:
                raise Namel3ssError("Unexpected indentation level.", line=current.line, column=current.column)
            if parse_binding_line(self, current, bindings_data):
                self._advance()
                continue
            if not current.text.endswith(":"):
                raise Namel3ssError("two_pane only supports primary: and secondary: blocks.", line=current.line, column=current.column)
            pane_name = current.text[:-1].strip()
            if pane_name not in {"primary", "secondary"}:
                raise Namel3ssError("two_pane only supports primary: and secondary: blocks.", line=current.line, column=current.column)
            if pane_name == "primary" and primary is not None:
                raise Namel3ssError("primary is already declared.", line=current.line, column=current.column)
            if pane_name == "secondary" and secondary is not None:
                raise Namel3ssError("secondary is already declared.", line=current.line, column=current.column)
            self._advance()
            pane_children = self._parse_children(
                expected_indent=current.indent + _INDENT_WIDTH,
                parent_kind=f"two_pane.{pane_name}",
                ancestor_kinds=ancestor_kinds + ("two_pane", pane_name),
                drawer_triggers=drawer_triggers,
            )
            if not pane_children:
                raise Namel3ssError(f"{pane_name} pane must include at least one child.", line=current.line, column=current.column)
            if pane_name == "primary":
                primary = pane_children
            else:
                secondary = pane_children
        if primary is None or secondary is None:
            raise Namel3ssError("two_pane must declare both primary and secondary panes.", line=line.line, column=line.column)
        return ast.TwoPaneNode(
            primary=primary,
            secondary=secondary,
            bindings=build_bindings(bindings_data),
            line=line.line,
            column=line.column,
        )

    def _parse_three_pane(
        self,
        line: _SourceLine,
        *,
        ancestor_kinds: tuple[str, ...],
        drawer_triggers: tuple[str, ...],
    ) -> ast.ThreePaneNode:
        self._note_feature("three_pane", line)
        self._advance()
        bindings_data = empty_binding_values()
        panes: dict[str, list[ast.LayoutNode] | None] = {"left": None, "center": None, "right": None}
        expected_indent = line.indent + _INDENT_WIDTH
        while not self._at_end():
            current = self._current()
            if current.indent < expected_indent:
                break
            if current.indent > expected_indent:
                raise Namel3ssError("Unexpected indentation level.", line=current.line, column=current.column)
            if parse_binding_line(self, current, bindings_data):
                self._advance()
                continue
            if not current.text.endswith(":"):
                raise Namel3ssError(
                    "three_pane only supports left:, center:, and right: blocks.",
                    line=current.line,
                    column=current.column,
                )
            pane_name = current.text[:-1].strip()
            if pane_name not in panes:
                raise Namel3ssError(
                    "three_pane only supports left:, center:, and right: blocks.",
                    line=current.line,
                    column=current.column,
                )
            if panes[pane_name] is not None:
                raise Namel3ssError(f"{pane_name} is already declared.", line=current.line, column=current.column)
            self._advance()
            pane_children = self._parse_children(
                expected_indent=current.indent + _INDENT_WIDTH,
                parent_kind=f"three_pane.{pane_name}",
                ancestor_kinds=ancestor_kinds + ("three_pane", pane_name),
                drawer_triggers=drawer_triggers,
            )
            if not pane_children:
                raise Namel3ssError(f"{pane_name} pane must include at least one child.", line=current.line, column=current.column)
            panes[pane_name] = pane_children
        if any(value is None for value in panes.values()):
            raise Namel3ssError("three_pane must declare left, center, and right panes.", line=line.line, column=line.column)
        return ast.ThreePaneNode(
            left=panes["left"] or [],
            center=panes["center"] or [],
            right=panes["right"] or [],
            bindings=build_bindings(bindings_data),
            line=line.line,
            column=line.column,
        )

    def _note_feature(self, feature: str, line: _SourceLine) -> None:
        self._feature_uses.append(_FeatureUse(feature=feature, line=line.line, column=line.column))

    def _at_end(self) -> bool:
        return self._index >= len(self._lines)

    def _current(self) -> _SourceLine:
        return self._lines[self._index]

    def _advance(self) -> None:
        self._index += 1
def _scan_source(source: str) -> list[_SourceLine]:
    rows: list[_SourceLine] = []
    for number, raw in enumerate(source.splitlines(), start=1):
        comment_cut = raw.split("#", 1)[0]
        if not comment_cut.strip():
            continue
        leading = raw[: len(raw) - len(raw.lstrip(" \t"))]
        if "\t" in leading:
            raise Namel3ssError("Tabs are not allowed for indentation.", line=number, column=1)
        indent = len(comment_cut) - len(comment_cut.lstrip(" "))
        if indent % _INDENT_WIDTH != 0:
            raise Namel3ssError(
                f"Indentation must use multiples of {_INDENT_WIDTH} spaces.",
                line=number,
                column=indent + 1,
            )
        rows.append(_SourceLine(line=number, indent=indent, column=indent + 1, text=comment_cut.strip()))
    return rows

__all__ = ["REQUIRED_CAPABILITY", "parse_layout_page"]
