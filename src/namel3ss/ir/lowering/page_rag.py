from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.ir import nodes as ir
from namel3ss.ir.lowering.expressions import _lower_expression


def _lower_citation_chips_item(item: ast.CitationChipsItem, *, attach_origin) -> ir.CitationChipsItem:
    source = _ensure_state_path(_lower_expression(item.source), "Citations must bind to state.<path>", item)
    return attach_origin(ir.CitationChipsItem(source=source, line=item.line, column=item.column), item)


def _lower_source_preview_item(item: ast.SourcePreviewItem, *, attach_origin) -> ir.SourcePreviewItem:
    source = _lower_expression(item.source)
    if isinstance(source, ir.StatePath):
        return attach_origin(ir.SourcePreviewItem(source=source, line=item.line, column=item.column), item)
    if isinstance(source, ir.Literal):
        if not isinstance(source.value, str):
            raise Namel3ssError("Source previews require a text source_id or url.", line=item.line, column=item.column)
        return attach_origin(ir.SourcePreviewItem(source=source, line=item.line, column=item.column), item)
    raise Namel3ssError(
        "Source previews require state.<path> or a text source_id.",
        line=item.line,
        column=item.column,
    )


def _lower_trust_indicator_item(item: ast.TrustIndicatorItem, *, attach_origin) -> ir.TrustIndicatorItem:
    source = _ensure_state_path(_lower_expression(item.source), "Trust indicators must bind to state.<path>", item)
    return attach_origin(ir.TrustIndicatorItem(source=source, line=item.line, column=item.column), item)


def _lower_scope_selector_item(item: ast.ScopeSelectorItem, *, attach_origin) -> ir.ScopeSelectorItem:
    options_source = _ensure_state_path(
        _lower_expression(item.options_source),
        "Scope selectors must bind options to state.<path>",
        item,
    )
    active = _ensure_state_path(
        _lower_expression(item.active),
        "Scope selectors must bind active selections to state.<path>",
        item,
    )
    return attach_origin(
        ir.ScopeSelectorItem(options_source=options_source, active=active, line=item.line, column=item.column),
        item,
    )


def _ensure_state_path(value: object, message: str, item: ast.Node) -> ir.StatePath:
    if isinstance(value, ir.StatePath):
        return value
    raise Namel3ssError(message, line=item.line, column=item.column)


__all__ = [
    "_lower_citation_chips_item",
    "_lower_scope_selector_item",
    "_lower_source_preview_item",
    "_lower_trust_indicator_item",
]
