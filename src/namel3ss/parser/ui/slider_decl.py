from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.parser.decl.page_common import (
    _is_visibility_rule_start,
    _parse_debug_only_clause,
    _parse_number_value,
    _parse_reference_name_value,
    _parse_show_when_clause,
    _parse_state_path_value,
    _parse_string_value,
    _parse_visibility_clause,
    _parse_visibility_rule_line,
    _validate_visibility_combo,
)


_SLIDER_REQUIRED_ERROR = "slider requires 'min', 'max', 'step', 'value', and 'on change'."


def parse_slider_item(parser, tok, *, allow_pattern_params: bool = False) -> ast.SliderItem:
    parser._advance()
    label = _parse_string_value(parser, allow_pattern_params=allow_pattern_params, context="slider label")
    if not isinstance(label, str):
        raise Namel3ssError(_SLIDER_REQUIRED_ERROR, line=tok.line, column=tok.column)
    visibility = _parse_visibility_clause(parser, allow_pattern_params=allow_pattern_params)
    show_when = _parse_show_when_clause(parser, allow_pattern_params=allow_pattern_params)
    debug_only = _parse_debug_only_clause(parser)
    parser._expect("COLON", "Expected ':' after slider label")
    parser._expect("NEWLINE", "Expected newline after slider header")
    parser._expect("INDENT", "Expected indented slider body")

    min_value: float | None = None
    max_value: float | None = None
    step: float | None = None
    value: ast.StatePath | None = None
    flow_name: str | None = None
    help_text: str | None = None
    visibility_rule: ast.VisibilityRule | ast.VisibilityExpressionRule | None = None

    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        if _is_visibility_rule_start(parser):
            if visibility_rule is not None:
                rule_tok = parser._current()
                raise Namel3ssError(
                    "Visibility blocks may only declare one only-when rule.",
                    line=rule_tok.line,
                    column=rule_tok.column,
                )
            visibility_rule = _parse_visibility_rule_line(parser, allow_pattern_params=allow_pattern_params)
            parser._match("NEWLINE")
            continue

        field_tok = parser._current()
        if field_tok.type != "IDENT":
            raise Namel3ssError(_SLIDER_REQUIRED_ERROR, line=field_tok.line, column=field_tok.column)

        if field_tok.value == "min":
            _reject_duplicate(min_value, "min", field_tok)
            parser._advance()
            parser._expect("IS", "Expected 'is' after min")
            parsed = _parse_number_value(parser, allow_pattern_params=False)
            min_value = float(parsed)
            parser._match("NEWLINE")
            continue

        if field_tok.value == "max":
            _reject_duplicate(max_value, "max", field_tok)
            parser._advance()
            parser._expect("IS", "Expected 'is' after max")
            parsed = _parse_number_value(parser, allow_pattern_params=False)
            max_value = float(parsed)
            parser._match("NEWLINE")
            continue

        if field_tok.value == "step":
            _reject_duplicate(step, "step", field_tok)
            parser._advance()
            parser._expect("IS", "Expected 'is' after step")
            parsed = _parse_number_value(parser, allow_pattern_params=False)
            step = float(parsed)
            parser._match("NEWLINE")
            continue

        if field_tok.value == "value":
            _reject_duplicate(value, "value", field_tok)
            parser._advance()
            parser._expect("IS", "Expected 'is' after value")
            parsed_path = _parse_state_path_value(parser, allow_pattern_params=False)
            if not isinstance(parsed_path, ast.StatePath):
                raise Namel3ssError(_SLIDER_REQUIRED_ERROR, line=field_tok.line, column=field_tok.column)
            value = parsed_path
            parser._match("NEWLINE")
            continue

        if field_tok.value == "on":
            _reject_duplicate(flow_name, "on change", field_tok)
            parser._advance()
            change_tok = parser._current()
            parser._advance()
            if str(change_tok.value) != "change":
                raise Namel3ssError(_SLIDER_REQUIRED_ERROR, line=change_tok.line, column=change_tok.column)
            run_tok = parser._current()
            parser._advance()
            if str(run_tok.value) != "run":
                raise Namel3ssError(_SLIDER_REQUIRED_ERROR, line=run_tok.line, column=run_tok.column)
            parsed_flow = _parse_reference_name_value(parser, allow_pattern_params=False, context="flow")
            if not isinstance(parsed_flow, str) or not parsed_flow.strip():
                raise Namel3ssError(_SLIDER_REQUIRED_ERROR, line=field_tok.line, column=field_tok.column)
            flow_name = parsed_flow.strip()
            parser._match("NEWLINE")
            continue

        if field_tok.value == "help":
            _reject_duplicate(help_text, "help", field_tok)
            parser._advance()
            parser._expect("IS", "Expected 'is' after help")
            parsed_help = _parse_string_value(parser, allow_pattern_params=False, context="slider help")
            if not isinstance(parsed_help, str) or not parsed_help.strip():
                raise Namel3ssError("tooltip text cannot be empty.", line=field_tok.line, column=field_tok.column)
            help_text = parsed_help.strip()
            parser._match("NEWLINE")
            continue

        raise Namel3ssError(_SLIDER_REQUIRED_ERROR, line=field_tok.line, column=field_tok.column)

    parser._expect("DEDENT", "Expected end of slider body")
    if min_value is None or max_value is None or step is None or value is None or flow_name is None:
        raise Namel3ssError(_SLIDER_REQUIRED_ERROR, line=tok.line, column=tok.column)
    _validate_visibility_combo(visibility, visibility_rule, line=tok.line, column=tok.column)
    return ast.SliderItem(
        label=label,
        min_value=min_value,
        max_value=max_value,
        step=step,
        value=value,
        flow_name=flow_name,
        help_text=help_text,
        visibility=visibility,
        visibility_rule=visibility_rule,
        show_when=show_when,
        debug_only=debug_only,
        line=tok.line,
        column=tok.column,
    )


def _reject_duplicate(value: object, field_name: str, tok) -> None:
    if value is None:
        return
    raise Namel3ssError(f"slider field '{field_name}' is declared more than once.", line=tok.line, column=tok.column)


__all__ = ["parse_slider_item"]
