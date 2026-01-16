from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.ir.model.pages import NumberEntry, NumberItem
from namel3ss.schema import records as schema


def lower_number_item(
    item: ast.NumberItem,
    record_map: dict[str, schema.RecordSchema],
    *,
    attach_origin,
    unknown_record_message,
) -> NumberItem:
    entries: list[NumberEntry] = []
    for entry in item.entries:
        if entry.kind == "count":
            if entry.record_name not in record_map:
                raise Namel3ssError(
                    unknown_record_message(entry.record_name, record_map),
                    line=entry.line,
                    column=entry.column,
                )
            entries.append(
                NumberEntry(
                    kind="count",
                    record_name=entry.record_name,
                    label=entry.label,
                    line=entry.line,
                    column=entry.column,
                )
            )
        else:
            if not entry.value:
                raise Namel3ssError("Number phrase is empty", line=entry.line, column=entry.column)
            entries.append(NumberEntry(kind="phrase", value=entry.value, line=entry.line, column=entry.column))
    return attach_origin(NumberItem(entries=entries, line=item.line, column=item.column), item)


__all__ = ["lower_number_item"]
