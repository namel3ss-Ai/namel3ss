from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.ir import nodes as ir
from namel3ss.ir.lowering.expressions import _lower_expression
from namel3ss.runtime.records.state_paths import record_state_path
from namel3ss.schema import records as schema

_ALLOWED_CHART_TYPES = {"bar", "line", "summary"}


def _lower_chart_item(
    item: ast.ChartItem,
    record_map: dict[str, schema.RecordSchema],
    page_name: str,
) -> ir.ChartItem:
    if item.record_name and item.source:
        raise Namel3ssError("Charts must use either a record or state source, not both", line=item.line, column=item.column)
    if not item.record_name and not item.source:
        raise Namel3ssError("Charts must use a record or state source", line=item.line, column=item.column)
    chart_type = item.chart_type.lower() if item.chart_type else "summary"
    if chart_type not in _ALLOWED_CHART_TYPES:
        raise Namel3ssError(
            f"Chart type '{chart_type}' is not supported",
            line=item.line,
            column=item.column,
        )
    source = _lower_expression(item.source) if item.source else None
    if source is not None and not isinstance(source, ir.StatePath):
        raise Namel3ssError("Charts must bind to state.<path>", line=item.line, column=item.column)
    record_name = item.record_name
    if record_name:
        if record_name not in record_map:
            raise Namel3ssError(
                f"Page '{page_name}' references unknown record '{record_name}'",
                line=item.line,
                column=item.column,
            )
        record = record_map[record_name]
        if item.x and item.x not in record.field_map:
            raise Namel3ssError(
                f"Chart x field '{item.x}' is not part of record '{record.name}'",
                line=item.line,
                column=item.column,
            )
        if item.y and item.y not in record.field_map:
            raise Namel3ssError(
                f"Chart y field '{item.y}' is not part of record '{record.name}'",
                line=item.line,
                column=item.column,
            )
    return ir.ChartItem(
        record_name=record_name,
        source=source,
        chart_type=chart_type,
        x=item.x,
        y=item.y,
        explain=item.explain,
        line=item.line,
        column=item.column,
    )


def _validate_chart_pairing(items: list[ir.PageItem], page_name: str) -> None:
    record_sources: set[str] = set()
    charts: list[ir.ChartItem] = []
    for item in _walk_items(items):
        if isinstance(item, (ir.TableItem, ir.ListItem)):
            record_sources.add(item.record_name)
        if isinstance(item, ir.ChartItem):
            charts.append(item)
    if not charts:
        return
    for chart in charts:
        if chart.record_name:
            if chart.record_name not in record_sources:
                raise Namel3ssError(
                    f"Chart for record '{chart.record_name}' must be paired with a table or list on page '{page_name}'",
                    line=chart.line,
                    column=chart.column,
                )
            continue
        if chart.source is None:
            continue
        if not _state_chart_paired(chart.source, record_sources):
            source_label = f"state.{'.'.join(chart.source.path)}"
            raise Namel3ssError(
                f"Chart from {source_label} must be paired with a table or list using the same data source",
                line=chart.line,
                column=chart.column,
            )


def _state_chart_paired(source: ir.StatePath, record_sources: set[str]) -> bool:
    for record_name in record_sources:
        if record_state_path(record_name) == source.path:
            return True
    return False


def _walk_items(items: list[ir.PageItem]) -> list[ir.PageItem]:
    collected: list[ir.PageItem] = []
    for item in items:
        collected.append(item)
        if isinstance(item, (ir.SectionItem, ir.CardGroupItem, ir.CardItem, ir.RowItem, ir.ColumnItem)):
            collected.extend(_walk_items(item.children))
            continue
        if isinstance(item, (ir.ModalItem, ir.DrawerItem)):
            collected.extend(_walk_items(item.children))
            continue
        if isinstance(item, ir.TabsItem):
            for tab in item.tabs:
                collected.extend(_walk_items(tab.children))
            continue
    return collected


__all__ = ["_lower_chart_item", "_validate_chart_pairing"]
