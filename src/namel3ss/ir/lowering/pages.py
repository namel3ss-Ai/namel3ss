from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.ir.model.pages import (
    ButtonItem,
    CardItem,
    ColumnItem,
    DividerItem,
    FormItem,
    ImageItem,
    Page,
    PageItem,
    RowItem,
    SectionItem,
    TableItem,
    TextItem,
    TitleItem,
)
from namel3ss.schema import records as schema
from namel3ss.ir.lowering.expressions import _lower_expression


def _lower_page(page: ast.PageDecl, record_map: dict[str, schema.RecordSchema], flow_names: set[str]) -> Page:
    items = [_lower_page_item(item, record_map, flow_names, page.name) for item in page.items]
    return Page(
        name=page.name,
        items=items,
        requires=_lower_expression(page.requires) if page.requires else None,
        line=page.line,
        column=page.column,
    )


def _lower_page_item(
    item: ast.PageItem,
    record_map: dict[str, schema.RecordSchema],
    flow_names: set[str],
    page_name: str,
) -> PageItem:
    if isinstance(item, ast.TitleItem):
        return TitleItem(value=item.value, line=item.line, column=item.column)
    if isinstance(item, ast.TextItem):
        return TextItem(value=item.value, line=item.line, column=item.column)
    if isinstance(item, ast.FormItem):
        if item.record_name not in record_map:
            raise Namel3ssError(
                f"Page '{page_name}' references unknown record '{item.record_name}'",
                line=item.line,
                column=item.column,
            )
        return FormItem(record_name=item.record_name, line=item.line, column=item.column)
    if isinstance(item, ast.TableItem):
        if item.record_name not in record_map:
            raise Namel3ssError(
                f"Page '{page_name}' references unknown record '{item.record_name}'",
                line=item.line,
                column=item.column,
            )
        return TableItem(record_name=item.record_name, line=item.line, column=item.column)
    if isinstance(item, ast.ButtonItem):
        if item.flow_name not in flow_names:
            raise Namel3ssError(
                f"Page '{page_name}' references unknown flow '{item.flow_name}'",
                line=item.line,
                column=item.column,
            )
        return ButtonItem(label=item.label, flow_name=item.flow_name, line=item.line, column=item.column)
    if isinstance(item, ast.SectionItem):
        children = [_lower_page_item(child, record_map, flow_names, page_name) for child in item.children]
        return SectionItem(label=item.label, children=children, line=item.line, column=item.column)
    if isinstance(item, ast.CardItem):
        children = [_lower_page_item(child, record_map, flow_names, page_name) for child in item.children]
        return CardItem(label=item.label, children=children, line=item.line, column=item.column)
    if isinstance(item, ast.RowItem):
        lowered_children: list[PageItem] = []
        for child in item.children:
            if not isinstance(child, ast.ColumnItem):
                raise Namel3ssError("Rows may only contain columns", line=child.line, column=child.column)
            lowered_children.append(_lower_page_item(child, record_map, flow_names, page_name))
        return RowItem(children=lowered_children, line=item.line, column=item.column)
    if isinstance(item, ast.ColumnItem):
        children = [_lower_page_item(child, record_map, flow_names, page_name) for child in item.children]
        return ColumnItem(children=children, line=item.line, column=item.column)
    if isinstance(item, ast.DividerItem):
        return DividerItem(line=item.line, column=item.column)
    if isinstance(item, ast.ImageItem):
        alt = item.alt if item.alt is not None else ""
        return ImageItem(src=item.src, alt=alt, line=item.line, column=item.column)
    raise TypeError(f"Unhandled page item type: {type(item)}")
