from __future__ import annotations

import difflib

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.foreign.types import is_foreign_type, normalize_foreign_type
from namel3ss.ir import nodes as ir
from namel3ss.ir.lowering.expressions import _lower_expression
from namel3ss.lexer.lexer import Lexer
from namel3ss.parser.core import Parser
from namel3ss.runtime.flow.gates import parse_state_requires
from namel3ss.runtime.values.types import type_name_for_value
from namel3ss.schema.records import FieldSchema, RecordSchema
from namel3ss.validation import ValidationMode, add_warning


def parse_selector_expression(selector: str, *, line: int | None, column: int | None) -> ir.Expression:
    try:
        tokens = Lexer(selector).tokenize()
        parser = Parser(tokens, allow_legacy_type_aliases=True, require_spec=False)
        expr = parser._parse_expression()
        parser._expect("EOF")
    except Namel3ssError as exc:
        raise Namel3ssError(
            build_guidance_message(
                what="Selector string is invalid.",
                why="Selectors must be simple comparisons like <field> is <value>.",
                fix='Use a selector like "id is 1".',
                example='where "id is 1"',
            ),
            line=line,
            column=column,
        ) from exc
    lowered = _lower_expression(expr)
    _validate_selector_expr(lowered, line=line, column=column)
    return lowered


def validate_declarative_flow(
    flow: ir.Flow,
    record_map: dict[str, RecordSchema],
    tool_map: dict[str, ir.ToolDecl],
    *,
    mode: ValidationMode,
    warnings: list | None,
) -> None:
    input_fields: dict[str, ir.FlowInputField] = {}
    saw_input = False
    steps = getattr(flow, "steps", None) or []
    for step in steps:
        if isinstance(step, ir.FlowInput):
            if saw_input:
                raise Namel3ssError(
                    build_guidance_message(
                        what="Flow declares input more than once.",
                        why="Declarative flows may only declare a single input block.",
                        fix="Combine the input fields into one input block.",
                        example='flow "demo"\n  input\n    name is text',
                    ),
                    line=step.line,
                    column=step.column,
                )
            saw_input = True
            for field in step.fields:
                if field.name in input_fields:
                    raise Namel3ssError(
                        build_guidance_message(
                            what=f"Input field '{field.name}' is duplicated.",
                            why="Input fields must be unique.",
                            fix="Remove the duplicate or rename it.",
                            example='input\n  name is text\n  email is text',
                        ),
                        line=field.line,
                        column=field.column,
                    )
                input_fields[field.name] = field
            continue
        if isinstance(step, ir.FlowRequire):
            _validate_require(step, mode=mode, warnings=warnings)
            continue
        if isinstance(step, ir.FlowCallForeign):
            _validate_call_foreign(step, tool_map, input_fields, line=step.line, column=step.column)
            continue
        if isinstance(step, ir.FlowCreate):
            record = _require_record(step.record_name, record_map, line=step.line, column=step.column)
            _validate_field_values(
                step.fields,
                record,
                input_fields,
                verb="create",
            )
            continue
        if isinstance(step, ir.FlowUpdate):
            record = _require_record(step.record_name, record_map, line=step.line, column=step.column)
            if step.selector is None:
                raise Namel3ssError(
                    build_guidance_message(
                        what="Update step is missing a where selector.",
                        why="Declarative updates require a selector to target records.",
                        fix='Add a where line like `where "id is 1"`.',
                        example='update "Order"\n  where "id is 1"\n  set\n    status is "shipped"',
                    ),
                    line=step.line,
                    column=step.column,
                )
            _validate_selector(step.selector, record, line=step.line, column=step.column)
            _validate_field_values(
                step.updates,
                record,
                input_fields,
                verb="update",
            )
            continue
        if isinstance(step, ir.FlowDelete):
            record = _require_record(step.record_name, record_map, line=step.line, column=step.column)
            if step.selector is None:
                raise Namel3ssError(
                    build_guidance_message(
                        what="Delete step is missing a where selector.",
                        why="Declarative deletes require a selector to target records.",
                        fix='Add a where line like `where "id is 1"`.',
                        example='delete "Order"\n  where "id is 1"',
                    ),
                    line=step.line,
                    column=step.column,
                )
            _validate_selector(step.selector, record, line=step.line, column=step.column)
            continue
        raise Namel3ssError(
            build_guidance_message(
                what="Flow step type is not supported.",
                why="Declarative flows only allow input, require, call foreign, create, update, and delete steps.",
                fix="Use one of the supported steps.",
                example='flow "demo"\n  input\n    name is text',
            ),
            line=getattr(step, "line", None),
            column=getattr(step, "column", None),
        )


def _validate_require(step: ir.FlowRequire, *, mode: ValidationMode, warnings: list | None) -> None:
    if mode != ValidationMode.STATIC:
        return
    path = parse_state_requires(step.condition)
    if path is None:
        add_warning(
            warnings,
            code="requires.skipped",
            message=f"Flow requires '{step.condition}' is not evaluated at static time.",
            fix="Use a state.<path> requires condition or validate it at runtime.",
            line=step.line,
            column=step.column,
            enforced_at="runtime",
        )
        return
    if not path:
        add_warning(
            warnings,
            code="state.invalid",
            message="Flow requires state path is malformed.",
            fix="Use state.<path> or remove the requires rule.",
            line=step.line,
            column=step.column,
        )


def _validate_field_values(
    fields: list[ir.FlowField],
    record: RecordSchema,
    input_fields: dict[str, ir.FlowInputField],
    *,
    verb: str,
) -> None:
    for field in fields:
        schema_field = _require_field(record, field.name, line=field.line, column=field.column)
        value_type = _value_type(field.value, input_fields, line=field.line, column=field.column)
        if schema_field.type_name == "json":
            continue
        if value_type != schema_field.type_name:
            raise Namel3ssError(
                build_guidance_message(
                    what=f"{record.name}.{field.name} expects {schema_field.type_name} but got {value_type}.",
                    why=f"{verb.title()} values must match the record field type.",
                    fix=f"Provide a {schema_field.type_name} value or change the field type.",
                    example=f'{field.name} is "{schema_field.type_name}_value"',
                ),
                line=field.line,
                column=field.column,
            )


def _value_type(
    expr: ir.Expression,
    input_fields: dict[str, ir.FlowInputField],
    *,
    line: int | None,
    column: int | None,
) -> str:
    if isinstance(expr, ir.Literal):
        if expr.value is None:
            raise Namel3ssError(
                build_guidance_message(
                    what="Null values are not allowed in declarative flows.",
                    why="Declarative values must be text, number, or boolean literals.",
                    fix="Provide a non-null literal or an input binding.",
                    example='status is "new"',
                ),
                line=line,
                column=column,
            )
        return type_name_for_value(expr.value)
    if isinstance(expr, ir.AttrAccess) and expr.base == "input" and len(expr.attrs) == 1:
        field_name = expr.attrs[0]
        field = input_fields.get(field_name)
        if field is None:
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Input field '{field_name}' is not declared.",
                    why="Input bindings must match fields in the input block.",
                    fix="Add the field to input or update the binding.",
                    example=f'input\n  {field_name} is text',
                ),
                line=line,
                column=column,
            )
        return field.type_name
    raise Namel3ssError(
        build_guidance_message(
            what="Declarative values must be literals or input bindings.",
            why="Expressions, state references, and function calls are not supported.",
            fix="Use a string/number/boolean literal or input.<field>.",
            example='name is input.name',
        ),
        line=line,
        column=column,
    )


def _validate_call_foreign(
    step: ir.FlowCallForeign,
    tool_map: dict[str, ir.ToolDecl],
    input_fields: dict[str, ir.FlowInputField],
    *,
    line: int | None,
    column: int | None,
) -> None:
    foreign_tools = {
        name: tool for name, tool in tool_map.items() if getattr(tool, "declared_as", "tool") == "foreign"
    }
    foreign = foreign_tools.get(step.foreign_name)
    if foreign is None:
        suggestion = difflib.get_close_matches(step.foreign_name, sorted(foreign_tools.keys()), n=1, cutoff=0.6)
        hint = f" Did you mean '{suggestion[0]}'?" if suggestion else ""
        raise Namel3ssError(
            build_guidance_message(
                what=f'Foreign function "{step.foreign_name}" is not declared.{hint}',
                why="Declarative flows can only call declared foreign functions.",
                fix="Declare the foreign function or update the call name.",
                example=_foreign_decl_example(step.foreign_name),
            ),
            line=line,
            column=column,
        )
    if getattr(foreign, "declared_as", "tool") != "foreign":
        raise Namel3ssError(
            build_guidance_message(
                what=f'Foreign function "{step.foreign_name}" is not declared as foreign.',
                why="The name refers to a tool declaration, not a foreign function.",
                fix="Declare it with a foreign function block or call the tool directly.",
                example=_foreign_decl_example(step.foreign_name),
            ),
            line=line,
            column=column,
        )
    arg_map = {arg.name: arg for arg in step.arguments}
    declared_fields = {field.name: field for field in foreign.input_fields}
    for arg_name in arg_map:
        if arg_name not in declared_fields:
            raise Namel3ssError(
                build_guidance_message(
                    what=f'Foreign function "{step.foreign_name}" has no input "{arg_name}".',
                    why="Call inputs must match the foreign function input block.",
                    fix="Remove the extra input or add it to the foreign declaration.",
                    example=_foreign_decl_example(step.foreign_name),
                ),
                line=arg_map[arg_name].line,
                column=arg_map[arg_name].column,
            )
    for field_name, field in declared_fields.items():
        if field_name not in arg_map:
            raise Namel3ssError(
                build_guidance_message(
                    what=f'Foreign function "{step.foreign_name}" is missing input "{field_name}".',
                    why="All foreign inputs are required.",
                    fix="Provide the missing input in the call.",
                    example=f'call foreign "{step.foreign_name}"\n  {field_name} is "value"',
                ),
                line=line,
                column=column,
            )
    for field_name, arg in arg_map.items():
        expected_raw = declared_fields[field_name].type_name
        expected, _ = normalize_foreign_type(expected_raw)
        if not is_foreign_type(expected):
            raise Namel3ssError(
                build_guidance_message(
                    what=f'Foreign function "{step.foreign_name}" has unsupported input type "{expected_raw}".',
                    why="Foreign inputs must be text, number, boolean, or list of those types.",
                    fix="Update the foreign declaration to a supported type.",
                    example=_foreign_decl_example(step.foreign_name),
                ),
                line=declared_fields[field_name].line,
                column=declared_fields[field_name].column,
            )
        actual = _value_type(arg.value, input_fields, line=arg.line, column=arg.column)
        if expected.startswith("list of "):
            if actual != "list":
                raise Namel3ssError(
                    build_guidance_message(
                        what=f'Foreign input "{field_name}" expects {expected} but got {actual}.',
                        why="Foreign inputs must match the declared type.",
                        fix=f"Provide a {expected} value or update the declaration.",
                        example=f'{field_name} is input.{field_name}',
                    ),
                    line=arg.line,
                    column=arg.column,
                )
            continue
        if actual != expected:
            raise Namel3ssError(
                build_guidance_message(
                    what=f'Foreign input "{field_name}" expects {expected} but got {actual}.',
                    why="Foreign inputs must match the declared type.",
                    fix=f"Provide a {expected} value or update the declaration.",
                    example=f'{field_name} is "value"',
                ),
                line=arg.line,
                column=arg.column,
            )


def _foreign_decl_example(name: str) -> str:
    return (
        f'foreign python function "{name}"\n'
        "  input\n"
        "    amount is number\n"
        "  output is number"
    )


def _require_record(
    name: str,
    record_map: dict[str, RecordSchema],
    *,
    line: int | None,
    column: int | None,
) -> RecordSchema:
    if name in record_map:
        return record_map[name]
    suggestion = difflib.get_close_matches(name, record_map.keys(), n=1, cutoff=0.6)
    hint = f' Did you mean "{suggestion[0]}"?' if suggestion else ""
    raise Namel3ssError(
        build_guidance_message(
            what=f"Unknown record '{name}'.{hint}",
            why="Declarative steps must reference declared records.",
            fix="Define the record or update the record name.",
            example=f'record "{name}":\n  id is number',
        ),
        line=line,
        column=column,
    )


def _require_field(
    record: RecordSchema,
    field_name: str,
    *,
    line: int | None,
    column: int | None,
) -> FieldSchema:
    if field_name in record.field_map:
        return record.field_map[field_name]
    suggestion = difflib.get_close_matches(field_name, record.field_map.keys(), n=1, cutoff=0.6)
    hint = f' Did you mean "{suggestion[0]}"?' if suggestion else ""
    sample = next(iter(record.field_map.keys()), "field")
    raise Namel3ssError(
        build_guidance_message(
            what=f"Unknown field '{field_name}' in record '{record.name}'.{hint}",
            why="Field assignments must match declared record fields.",
            fix="Use a field declared on the record.",
            example=f'create "{record.name}"\n  {sample} is "value"',
        ),
        line=line,
        column=column,
    )


def _validate_selector(selector: str, record: RecordSchema, *, line: int | None, column: int | None) -> None:
    expr = parse_selector_expression(selector, line=line, column=column)
    if not isinstance(expr, ir.Comparison) or expr.kind != "eq":
        raise Namel3ssError(
            build_guidance_message(
                what="Selector must be an equality comparison.",
                why="Declarative selectors are limited to <field> is <value>.",
                fix='Use a selector like "id is 1".',
                example='where "id is 1"',
            ),
            line=line,
            column=column,
        )
    if not isinstance(expr.left, ir.VarReference):
        raise Namel3ssError(
            build_guidance_message(
                what="Selector must compare a field name.",
                why="Declarative selectors require a record field on the left side.",
                fix='Use a selector like "id is 1".',
                example='where "id is 1"',
            ),
            line=line,
            column=column,
        )
    schema_field = _require_field(record, expr.left.name, line=line, column=column)
    if not isinstance(expr.right, ir.Literal) or expr.right.value is None:
        raise Namel3ssError(
            build_guidance_message(
                what="Selector value must be a literal.",
                why="Declarative selectors use literal values only.",
                fix='Use a selector like "id is 1".',
                example='where "id is 1"',
            ),
            line=line,
            column=column,
        )
    value_type = type_name_for_value(expr.right.value)
    field_type = schema_field.type_name
    if field_type != "json" and value_type != field_type:
        raise Namel3ssError(
            build_guidance_message(
                what=f"Selector value for {record.name}.{expr.left.name} must be {field_type}.",
                why="Selector values must match the field type.",
                fix=f"Provide a {field_type} literal.",
                example='where "id is 1"',
            ),
            line=line,
            column=column,
        )


def _validate_selector_expr(expr: ir.Expression, *, line: int | None, column: int | None) -> None:
    if not isinstance(expr, ir.Comparison):
        raise Namel3ssError(
            build_guidance_message(
                what="Selector must be a comparison.",
                why="Declarative selectors are limited to <field> is <value>.",
                fix='Use a selector like "id is 1".',
                example='where "id is 1"',
            ),
            line=line,
            column=column,
        )


__all__ = ["parse_selector_expression", "validate_declarative_flow"]
