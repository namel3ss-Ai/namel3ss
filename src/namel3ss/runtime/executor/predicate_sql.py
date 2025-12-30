from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from namel3ss.ir import nodes as ir
from namel3ss.runtime.executor.expr_eval import evaluate_expression
from namel3ss.runtime.storage.predicate import SqlPredicate
from namel3ss.runtime.storage.sql_helpers import quote_identifier, slug_identifier
from namel3ss.schema.records import FieldSchema, RecordSchema
from namel3ss.utils.numbers import decimal_to_str, is_number, to_decimal


_TEXT_TYPES = {"text", "string", "str"}
_NUMBER_TYPES = {"number", "int", "integer"}
_BOOLEAN_TYPES = {"boolean", "bool"}


class _UnsupportedPredicate(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class _SqlTerm:
    kind: str  # "column" or "value"
    field: FieldSchema | None = None
    value: object | None = None


@dataclass(frozen=True)
class _SqlBool:
    sql: str
    params: list[Any]


def compile_sql_predicate(
    ctx,
    schema: RecordSchema,
    expr: ir.Expression,
    *,
    dialect: str,
) -> tuple[SqlPredicate | None, str | None]:
    try:
        compiled = _SqlPredicateCompiler(ctx, schema, dialect).compile(expr)
    except _UnsupportedPredicate as exc:
        return None, exc.reason
    return SqlPredicate(clause=compiled.sql, params=compiled.params), None


class _SqlPredicateCompiler:
    def __init__(self, ctx, schema: RecordSchema, dialect: str) -> None:
        self._ctx = ctx
        self._schema = schema
        self._dialect = dialect
        self._placeholder = "?" if dialect == "sqlite" else "%s"

    def compile(self, expr: ir.Expression) -> _SqlBool:
        return self._compile_boolean(expr)

    def _compile_boolean(self, expr: ir.Expression) -> _SqlBool:
        if isinstance(expr, ir.BinaryOp) and expr.op in {"and", "or"}:
            left = self._compile_boolean(expr.left)
            right = self._compile_boolean(expr.right)
            op = "AND" if expr.op == "and" else "OR"
            sql = f"({left.sql}) {op} ({right.sql})"
            return _SqlBool(sql=sql, params=[*left.params, *right.params])
        if isinstance(expr, ir.UnaryOp) and expr.op == "not":
            inner = self._compile_boolean(expr.operand)
            return _SqlBool(sql=f"NOT ({inner.sql})", params=list(inner.params))
        if isinstance(expr, ir.Comparison):
            return self._compile_comparison(expr)
        raise _UnsupportedPredicate(f"Unsupported predicate expression: {type(expr).__name__}")

    def _compile_comparison(self, expr: ir.Comparison) -> _SqlBool:
        left = self._compile_term(expr.left)
        right = self._compile_term(expr.right)
        if left.kind == "value" and right.kind == "value":
            return self._constant_comparison(expr.kind, left.value, right.value)
        if left.kind == "column" and right.kind == "value":
            return self._column_value_comparison(expr.kind, left.field, right.value, flipped=False)
        if left.kind == "value" and right.kind == "column":
            return self._column_value_comparison(expr.kind, right.field, left.value, flipped=True)
        if left.kind == "column" and right.kind == "column":
            return self._column_column_comparison(expr.kind, left.field, right.field)
        raise _UnsupportedPredicate("Unsupported comparison operands")

    def _compile_term(self, expr: ir.Expression) -> _SqlTerm:
        if isinstance(expr, ir.VarReference) and expr.name in self._schema.field_map:
            return _SqlTerm(kind="column", field=self._schema.field_map[expr.name])
        if isinstance(expr, ir.AttrAccess) and expr.base in self._schema.field_map:
            raise _UnsupportedPredicate("Record attribute access is not supported in SQL predicates")
        if self._contains_field_reference(expr):
            raise _UnsupportedPredicate("Predicate expression contains unsupported record references")
        value = self._evaluate_constant(expr)
        return _SqlTerm(kind="value", value=value)

    def _contains_field_reference(self, expr: ir.Expression) -> bool:
        if isinstance(expr, ir.VarReference):
            return expr.name in self._schema.field_map
        if isinstance(expr, ir.AttrAccess):
            return expr.base in self._schema.field_map
        if isinstance(expr, ir.StatePath):
            return False
        if isinstance(expr, ir.Literal):
            return False
        if isinstance(expr, ir.UnaryOp):
            return self._contains_field_reference(expr.operand)
        if isinstance(expr, ir.BinaryOp):
            return self._contains_field_reference(expr.left) or self._contains_field_reference(expr.right)
        if isinstance(expr, ir.Comparison):
            return self._contains_field_reference(expr.left) or self._contains_field_reference(expr.right)
        return True

    def _evaluate_constant(self, expr: ir.Expression) -> object:
        try:
            return evaluate_expression(self._ctx, expr)
        except Exception as err:
            raise _UnsupportedPredicate(f"Constant predicate term failed to evaluate: {err}") from err

    def _constant_comparison(self, kind: str, left: object, right: object) -> _SqlBool:
        try:
            result = _compare_values(kind, left, right)
        except Exception as err:
            raise _UnsupportedPredicate(f"Constant comparison is not supported: {err}") from err
        return _SqlBool(sql=_constant_sql(result), params=[])

    def _column_value_comparison(
        self,
        kind: str,
        field: FieldSchema | None,
        value: object,
        *,
        flipped: bool,
    ) -> _SqlBool:
        if field is None:
            raise _UnsupportedPredicate("Missing record field for SQL comparison")
        if value is None:
            if kind == "eq":
                col = self._column_sql(field, numeric_compare=False)
                return _SqlBool(sql=f"{col} IS NULL", params=[])
            if kind == "ne":
                col = self._column_sql(field, numeric_compare=False)
                return _SqlBool(sql=f"{col} IS NOT NULL", params=[])
            raise _UnsupportedPredicate("Numeric comparison against null is not supported")
        value_type = _value_type(value)
        if kind in {"gt", "lt", "gte", "lte"}:
            if not _is_numeric_field(field) or value_type != "number":
                raise _UnsupportedPredicate("Numeric comparison requires numeric field and value")
            col = self._column_sql(field, numeric_compare=True)
            op = _sql_op(kind)
            param = self._serialize_value(field, value, numeric_compare=True)
            sql = f"{col} {op} {self._placeholder}"
            if flipped:
                sql = f"{self._placeholder} {op} {col}"
            return _SqlBool(sql=sql, params=[param])
        if not _types_compatible(field, value_type):
            raise _UnsupportedPredicate("Equality comparison requires compatible field/value types")
        col = self._column_sql(field, numeric_compare=False)
        op = _sql_op(kind)
        param = self._serialize_value(field, value, numeric_compare=False)
        sql = f"{col} {op} {self._placeholder}"
        if flipped:
            sql = f"{self._placeholder} {op} {col}"
        return _SqlBool(sql=sql, params=[param])

    def _column_column_comparison(self, kind: str, left: FieldSchema | None, right: FieldSchema | None) -> _SqlBool:
        if left is None or right is None:
            raise _UnsupportedPredicate("Missing record fields for SQL comparison")
        if kind in {"gt", "lt", "gte", "lte"}:
            if not _is_numeric_field(left) or not _is_numeric_field(right):
                raise _UnsupportedPredicate("Numeric comparison requires numeric fields")
            left_sql = self._column_sql(left, numeric_compare=True)
            right_sql = self._column_sql(right, numeric_compare=True)
            return _SqlBool(sql=f"{left_sql} {_sql_op(kind)} {right_sql}", params=[])
        if not _fields_compatible(left, right):
            raise _UnsupportedPredicate("Equality comparison requires compatible field types")
        left_sql = self._column_sql(left, numeric_compare=False)
        right_sql = self._column_sql(right, numeric_compare=False)
        return _SqlBool(sql=f"{left_sql} {_sql_op(kind)} {right_sql}", params=[])

    def _column_sql(self, field: FieldSchema, *, numeric_compare: bool) -> str:
        column = quote_identifier(slug_identifier(field.name))
        if numeric_compare and self._dialect == "sqlite":
            return f"CAST({column} AS REAL)"
        return column

    def _serialize_value(self, field: FieldSchema, value: object, *, numeric_compare: bool) -> object:
        name = field.type_name.lower()
        if name in {"int", "integer"}:
            return int(to_decimal(value))
        if name == "number":
            if self._dialect == "sqlite":
                if numeric_compare:
                    return float(to_decimal(value))
                return decimal_to_str(to_decimal(value))
            return to_decimal(value)
        if name in _BOOLEAN_TYPES:
            return 1 if value else 0 if self._dialect == "sqlite" else bool(value)
        return value


def _is_numeric_field(field: FieldSchema) -> bool:
    return field.type_name.lower() in _NUMBER_TYPES


def _types_compatible(field: FieldSchema, value_type: str) -> bool:
    name = field.type_name.lower()
    if name in _NUMBER_TYPES:
        return value_type == "number"
    if name in _TEXT_TYPES:
        return value_type == "text"
    if name in _BOOLEAN_TYPES:
        return value_type == "boolean"
    return False


def _fields_compatible(left: FieldSchema, right: FieldSchema) -> bool:
    left_type = left.type_name.lower()
    right_type = right.type_name.lower()
    if left_type in _NUMBER_TYPES and right_type in _NUMBER_TYPES:
        return True
    return left_type == right_type and left_type in (_TEXT_TYPES | _BOOLEAN_TYPES)


def _value_type(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if is_number(value):
        return "number"
    if isinstance(value, str):
        return "text"
    return "other"


def _sql_op(kind: str) -> str:
    if kind == "eq":
        return "="
    if kind == "ne":
        return "!="
    if kind == "gt":
        return ">"
    if kind == "lt":
        return "<"
    if kind == "gte":
        return ">="
    if kind == "lte":
        return "<="
    raise _UnsupportedPredicate(f"Unsupported comparison kind '{kind}'")


def _compare_values(kind: str, left: object, right: object) -> bool:
    if kind in {"gt", "lt", "gte", "lte"}:
        if not is_number(left) or not is_number(right):
            raise ValueError("Non-numeric comparison")
        left_num = to_decimal(left)
        right_num = to_decimal(right)
        if kind == "gt":
            return left_num > right_num
        if kind == "lt":
            return left_num < right_num
        if kind == "gte":
            return left_num >= right_num
        return left_num <= right_num
    if kind == "eq":
        if is_number(left) and is_number(right):
            return to_decimal(left) == to_decimal(right)
        return left == right
    if kind == "ne":
        if is_number(left) and is_number(right):
            return to_decimal(left) != to_decimal(right)
        return left != right
    raise ValueError("Unsupported comparison kind")


def _constant_sql(value: bool) -> str:
    return "1 = 1" if value else "1 = 0"


__all__ = ["compile_sql_predicate"]
