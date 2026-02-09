from __future__ import annotations

from decimal import Decimal

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.parser.decl.page_common import (
    _parse_debug_only_clause,
    _parse_optional_string_value,
    _parse_visibility_clause,
    _parse_show_when_clause,
    _parse_visibility_rule_block,
    _validate_visibility_combo,
)

_ALLOWED_LOADING_VARIANTS = {"spinner", "skeleton"}
_ALLOWED_ICON_SIZES = {"small", "medium", "large"}
_ALLOWED_ICON_ROLES = {"decorative", "semantic"}


def parse_loading_item(parser, tok, *, allow_pattern_params: bool = False) -> ast.LoadingItem:
    parser._advance()
    variant = "spinner"
    if parser._current().type == "IDENT" and parser._current().value == "variant":
        parser._advance()
        if parser._match("COLON"):
            pass
        else:
            parser._expect("IS", "Expected ':' or 'is' after variant")
        variant = _parse_ident_or_string(parser, context="loading variant")
    if variant not in _ALLOWED_LOADING_VARIANTS:
        raise Namel3ssError(
            f"Loading variant must be one of: {', '.join(sorted(_ALLOWED_LOADING_VARIANTS))}.",
            line=tok.line,
            column=tok.column,
        )
    visibility = _parse_visibility_clause(parser, allow_pattern_params=allow_pattern_params)
    show_when = _parse_show_when_clause(parser, allow_pattern_params=allow_pattern_params)
    debug_only = _parse_debug_only_clause(parser)
    visibility_rule = _parse_visibility_rule_block(parser, allow_pattern_params=allow_pattern_params)
    _validate_visibility_combo(visibility, visibility_rule, line=tok.line, column=tok.column)
    return ast.LoadingItem(
        variant=variant,
        visibility=visibility,
        visibility_rule=visibility_rule,
        show_when=show_when,
        debug_only=debug_only,
        line=tok.line,
        column=tok.column,
    )


def parse_snackbar_item(parser, tok, *, allow_pattern_params: bool = False) -> ast.SnackbarItem:
    parser._advance()
    message: str | None = None
    duration = 3000
    while parser._current().type not in {"NEWLINE", "DEDENT", "EOF"}:
        key_tok = parser._current()
        if key_tok.type != "IDENT":
            break
        key = str(key_tok.value)
        if key not in {"message", "duration"}:
            break
        parser._advance()
        if parser._match("COLON"):
            pass
        else:
            parser._expect("IS", f"Expected ':' or 'is' after {key}")
        if key == "message":
            if message is not None:
                raise Namel3ssError("Snackbar message is declared more than once", line=key_tok.line, column=key_tok.column)
            msg = _parse_optional_string_value(parser, allow_pattern_params=allow_pattern_params)
            if not isinstance(msg, str) or not msg:
                raise Namel3ssError("Snackbar message must be a non-empty string.", line=key_tok.line, column=key_tok.column)
            message = msg
        else:
            number_tok = parser._expect("NUMBER", "Snackbar duration must be a number")
            value = number_tok.value
            if isinstance(value, Decimal):
                if value != value.to_integral_value():
                    raise Namel3ssError("Snackbar duration must be an integer.", line=number_tok.line, column=number_tok.column)
                duration = int(value)
            else:
                duration = int(value)
            if duration < 0:
                raise Namel3ssError("Snackbar duration cannot be negative.", line=number_tok.line, column=number_tok.column)
    if message is None:
        raise Namel3ssError("Snackbar requires message.", line=tok.line, column=tok.column)
    visibility = _parse_visibility_clause(parser, allow_pattern_params=allow_pattern_params)
    show_when = _parse_show_when_clause(parser, allow_pattern_params=allow_pattern_params)
    debug_only = _parse_debug_only_clause(parser)
    visibility_rule = _parse_visibility_rule_block(parser, allow_pattern_params=allow_pattern_params)
    _validate_visibility_combo(visibility, visibility_rule, line=tok.line, column=tok.column)
    return ast.SnackbarItem(
        message=message,
        duration=duration,
        visibility=visibility,
        visibility_rule=visibility_rule,
        show_when=show_when,
        debug_only=debug_only,
        line=tok.line,
        column=tok.column,
    )


def parse_icon_item(parser, tok, *, allow_pattern_params: bool = False) -> ast.IconItem:
    parser._advance()
    name: str | None = None
    size = "medium"
    role = "decorative"
    label: str | None = None

    while parser._current().type not in {"NEWLINE", "DEDENT", "EOF"}:
        key_tok = parser._current()
        if key_tok.type != "IDENT":
            break
        key = str(key_tok.value)
        if key not in {"name", "size", "role", "label"}:
            break
        parser._advance()
        if parser._match("COLON"):
            pass
        else:
            parser._expect("IS", f"Expected ':' or 'is' after {key}")
        value = _parse_ident_or_string(parser, context=f"icon {key}")
        if key == "name":
            name = value
        elif key == "size":
            size = value
        elif key == "role":
            role = value
        else:
            label = value

    if not name:
        raise Namel3ssError("Icon requires name.", line=tok.line, column=tok.column)
    if size not in _ALLOWED_ICON_SIZES:
        raise Namel3ssError(
            f"Icon size must be one of: {', '.join(sorted(_ALLOWED_ICON_SIZES))}.",
            line=tok.line,
            column=tok.column,
        )
    if role not in _ALLOWED_ICON_ROLES:
        raise Namel3ssError(
            f"Icon role must be one of: {', '.join(sorted(_ALLOWED_ICON_ROLES))}.",
            line=tok.line,
            column=tok.column,
        )
    if role == "semantic" and not label:
        raise Namel3ssError(
            "Icon role semantic requires label for accessibility.",
            line=tok.line,
            column=tok.column,
        )

    visibility = _parse_visibility_clause(parser, allow_pattern_params=allow_pattern_params)
    show_when = _parse_show_when_clause(parser, allow_pattern_params=allow_pattern_params)
    debug_only = _parse_debug_only_clause(parser)
    visibility_rule = _parse_visibility_rule_block(parser, allow_pattern_params=allow_pattern_params)
    _validate_visibility_combo(visibility, visibility_rule, line=tok.line, column=tok.column)
    return ast.IconItem(
        name=name,
        size=size,
        role=role,
        label=label,
        visibility=visibility,
        visibility_rule=visibility_rule,
        show_when=show_when,
        debug_only=debug_only,
        line=tok.line,
        column=tok.column,
    )


def parse_lightbox_item(parser, tok, *, allow_pattern_params: bool = False) -> ast.LightboxItem:
    parser._advance()
    images: list[str] | None = None
    start_index = 0

    while parser._current().type not in {"NEWLINE", "DEDENT", "EOF"}:
        key_tok = parser._current()
        if key_tok.type != "IDENT":
            break
        key = str(key_tok.value)
        if key not in {"images", "startIndex", "start_index"}:
            break
        parser._advance()
        if parser._match("COLON"):
            pass
        else:
            parser._expect("IS", f"Expected ':' or 'is' after {key}")
        if key == "images":
            images = _parse_string_list(parser)
        else:
            number_tok = parser._expect("NUMBER", "Lightbox start index must be a number")
            value = number_tok.value
            if isinstance(value, Decimal):
                if value != value.to_integral_value():
                    raise Namel3ssError("Lightbox start index must be an integer.", line=number_tok.line, column=number_tok.column)
                start_index = int(value)
            else:
                start_index = int(value)
            if start_index < 0:
                raise Namel3ssError("Lightbox start index cannot be negative.", line=number_tok.line, column=number_tok.column)

    if not images:
        raise Namel3ssError("Lightbox requires at least one image.", line=tok.line, column=tok.column)

    visibility = _parse_visibility_clause(parser, allow_pattern_params=allow_pattern_params)
    show_when = _parse_show_when_clause(parser, allow_pattern_params=allow_pattern_params)
    debug_only = _parse_debug_only_clause(parser)
    visibility_rule = _parse_visibility_rule_block(parser, allow_pattern_params=allow_pattern_params)
    _validate_visibility_combo(visibility, visibility_rule, line=tok.line, column=tok.column)
    return ast.LightboxItem(
        images=images,
        start_index=start_index,
        visibility=visibility,
        visibility_rule=visibility_rule,
        show_when=show_when,
        debug_only=debug_only,
        line=tok.line,
        column=tok.column,
    )


def _parse_ident_or_string(parser, *, context: str) -> str:
    tok = parser._current()
    if tok.type == "STRING":
        parser._advance()
        return str(tok.value)
    if tok.type == "IDENT":
        parser._advance()
        return str(tok.value)
    raise Namel3ssError(f"Expected {context} value.", line=tok.line, column=tok.column)


def _parse_string_list(parser) -> list[str]:
    parser._expect("LBRACKET", "Expected '[' for list")
    values: list[str] = []
    while True:
        tok = parser._expect("STRING", "Lightbox images must be string paths")
        values.append(str(tok.value))
        if parser._match("COMMA"):
            continue
        break
    parser._expect("RBRACKET", "Expected ']' after list")
    return values


__all__ = [
    "parse_icon_item",
    "parse_lightbox_item",
    "parse_loading_item",
    "parse_snackbar_item",
]
