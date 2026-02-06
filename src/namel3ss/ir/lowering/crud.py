from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.ir.model.crud import CrudDefinition


def lower_crud(crud_defs: list[ast.CrudDefinition]) -> list[CrudDefinition]:
    return [
        CrudDefinition(record_name=crud.record_name, line=crud.line, column=crud.column)
        for crud in crud_defs
    ]


__all__ = ["lower_crud"]
