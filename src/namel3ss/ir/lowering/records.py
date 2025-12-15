from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.ir.lowering.expressions import _lower_expression
from namel3ss.schema import records as schema


def _lower_record(record: ast.RecordDecl) -> schema.RecordSchema:
    fields = []
    for field in record.fields:
        constraint = None
        if field.constraint:
            constraint = schema.FieldConstraint(
                kind=field.constraint.kind,
                expression=_lower_expression(field.constraint.expression) if field.constraint.expression else None,
                pattern=field.constraint.pattern,
            )
        fields.append(
            schema.FieldSchema(
                name=field.name,
                type_name=field.type_name,
                constraint=constraint,
            )
        )
    return schema.RecordSchema(name=record.name, fields=fields)
