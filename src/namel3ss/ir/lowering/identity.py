from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.ir.lowering.expressions import _lower_expression
from namel3ss.schema.identity import IdentitySchema
from namel3ss.schema import records as schema


def _lower_identity(identity: ast.IdentityDecl) -> IdentitySchema:
    fields = []
    for field in identity.fields:
        constraint = None
        if field.constraint:
            constraint = schema.FieldConstraint(
                kind=field.constraint.kind,
                expression=_lower_expression(field.constraint.expression) if field.constraint.expression else None,
                expression_high=_lower_expression(field.constraint.expression_high)
                if field.constraint.expression_high
                else None,
                pattern=field.constraint.pattern,
            )
        fields.append(
            schema.FieldSchema(
                name=field.name,
                type_name=field.type_name,
                constraint=constraint,
            )
        )
    return IdentitySchema(
        name=identity.name,
        fields=fields,
        trust_levels=list(identity.trust_levels) if identity.trust_levels else None,
        line=identity.line,
        column=identity.column,
    )
