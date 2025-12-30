from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.ir.lowering.expressions import _lower_expression
from namel3ss.schema import records as schema
from namel3ss.utils.numbers import is_number, to_decimal


def _lower_record(record: ast.RecordDecl) -> schema.RecordSchema:
    fields = []
    for field in record.fields:
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
    tenant_key = _lower_tenant_key(record.tenant_key) if record.tenant_key else None
    ttl_hours = _lower_ttl_hours(record.ttl_hours) if record.ttl_hours else None
    return schema.RecordSchema(
        name=record.name,
        fields=fields,
        tenant_key=tenant_key,
        ttl_hours=ttl_hours,
    )


def _lower_tenant_key(expr: ast.Expression) -> list[str]:
    if isinstance(expr, ast.AttrAccess) and expr.base == "identity":
        if not expr.attrs:
            raise Namel3ssError(
                build_guidance_message(
                    what="tenant_key must point to an identity field.",
                    why="A tenant_key needs a concrete identity field like organization_id.",
                    fix="Reference an identity field path.",
                    example="tenant_key is identity.organization_id",
                ),
                line=expr.line,
                column=expr.column,
            )
        return list(expr.attrs)
    raise Namel3ssError(
        build_guidance_message(
            what="tenant_key is not an identity path.",
            why="tenant_key must reference identity.<field>.",
            fix="Update tenant_key to use an identity field.",
            example="tenant_key is identity.organization_id",
        ),
        line=getattr(expr, "line", None),
        column=getattr(expr, "column", None),
    )


def _lower_ttl_hours(expr: ast.Expression) -> object:
    if isinstance(expr, ast.Literal) and is_number(expr.value):
        ttl_value = to_decimal(expr.value)
        if ttl_value <= 0:
            raise Namel3ssError(
                build_guidance_message(
                    what="ttl_hours must be greater than 0.",
                    why="A zero or negative TTL cannot be enforced.",
                    fix="Use a positive number of hours.",
                    example="ttl_hours is 24",
                ),
                line=expr.line,
                column=expr.column,
            )
        return ttl_value
    raise Namel3ssError(
        build_guidance_message(
            what="ttl_hours must be a numeric literal.",
            why="TTL is evaluated at parse time and must be a number.",
            fix="Provide a numeric literal for ttl_hours.",
            example="ttl_hours is 24",
        ),
        line=getattr(expr, "line", None),
        column=getattr(expr, "column", None),
    )
