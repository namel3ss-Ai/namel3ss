from __future__ import annotations

import re

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.lang.keywords import is_keyword
from namel3ss.parser.decl.page_common import (
    _is_param_ref,
    _parse_boolean_value,
    _parse_debug_only_clause,
    _parse_param_ref,
    _parse_show_when_clause,
    _parse_string_value,
    _parse_visibility_clause,
    _parse_visibility_rule_block,
    _parse_visibility_rule_line,
    _is_visibility_rule_start,
    _validate_visibility_combo,
)
from namel3ss.parser.diagnostics import reserved_identifier_diagnostic

_MIME_TYPE_RE = re.compile(r"^[A-Za-z0-9!#$&^_.+\-]+/[A-Za-z0-9!#$&^_.+*\-]+$")
_MIME_EXTENSION_RE = re.compile(r"^[A-Za-z0-9.+\-]+$")


def parse_upload_item(parser, tok, *, allow_pattern_params: bool = False) -> ast.UploadItem:
    parser._advance()
    if allow_pattern_params and _is_param_ref(parser):
        name = _parse_param_ref(parser)
    else:
        name_tok = parser._expect("IDENT", "Expected upload name")
        if is_keyword(name_tok.value) and not getattr(name_tok, "escaped", False):
            guidance, details = reserved_identifier_diagnostic(name_tok.value)
            raise Namel3ssError(guidance, line=name_tok.line, column=name_tok.column, details=details)
        name = name_tok.value
    visibility = _parse_visibility_clause(parser, allow_pattern_params=allow_pattern_params)
    show_when = _parse_show_when_clause(parser, allow_pattern_params=allow_pattern_params)
    debug_only = _parse_debug_only_clause(parser)
    visibility_rule = None
    accept = None
    multiple = None
    required = None
    label = None
    preview = None
    if parser._match("COLON"):
        parser._expect("NEWLINE", "Expected newline after upload header")
        parser._expect("INDENT", "Expected indented upload block")
        while parser._current().type != "DEDENT":
            if parser._match("NEWLINE"):
                continue
            entry_tok = parser._current()
            if _is_visibility_rule_start(parser):
                if visibility_rule is not None:
                    raise Namel3ssError(
                        "Visibility blocks may only declare one only-when rule.",
                        line=entry_tok.line,
                        column=entry_tok.column,
                    )
                visibility_rule = _parse_visibility_rule_line(parser, allow_pattern_params=allow_pattern_params)
                parser._match("NEWLINE")
                continue
            if entry_tok.type == "IDENT" and entry_tok.value == "accept":
                if accept is not None:
                    raise Namel3ssError("Accept is declared more than once", line=entry_tok.line, column=entry_tok.column)
                parser._advance()
                parser._expect("IS", "Expected 'is' after accept")
                accept = _parse_upload_accept_list(parser, line=entry_tok.line, column=entry_tok.column)
                if parser._match("NEWLINE"):
                    continue
                continue
            if entry_tok.type == "IDENT" and entry_tok.value == "multiple":
                if multiple is not None:
                    raise Namel3ssError("Multiple is declared more than once", line=entry_tok.line, column=entry_tok.column)
                parser._advance()
                parser._expect("IS", "Expected 'is' after multiple")
                try:
                    multiple = _parse_boolean_value(parser, allow_pattern_params=allow_pattern_params)
                except Namel3ssError as err:
                    raise Namel3ssError(
                        "Multiple must be true or false",
                        line=err.line,
                        column=err.column,
                    ) from err
                if parser._match("NEWLINE"):
                    continue
                continue
            if entry_tok.type == "IDENT" and entry_tok.value == "required":
                if required is not None:
                    raise Namel3ssError("Required is declared more than once", line=entry_tok.line, column=entry_tok.column)
                parser._advance()
                parser._expect("IS", "Expected 'is' after required")
                try:
                    required = _parse_boolean_value(parser, allow_pattern_params=allow_pattern_params)
                except Namel3ssError as err:
                    raise Namel3ssError(
                        "Required must be true or false",
                        line=err.line,
                        column=err.column,
                    ) from err
                if parser._match("NEWLINE"):
                    continue
                continue
            if entry_tok.type == "IDENT" and entry_tok.value == "label":
                if label is not None:
                    raise Namel3ssError("Label is declared more than once", line=entry_tok.line, column=entry_tok.column)
                parser._advance()
                parser._expect("IS", "Expected 'is' after label")
                label = _parse_string_value(parser, allow_pattern_params=allow_pattern_params, context="upload label")
                if parser._match("NEWLINE"):
                    continue
                continue
            if entry_tok.type == "IDENT" and entry_tok.value == "preview":
                if preview is not None:
                    raise Namel3ssError("Preview is declared more than once", line=entry_tok.line, column=entry_tok.column)
                parser._advance()
                parser._expect("IS", "Expected 'is' after preview")
                try:
                    preview = _parse_boolean_value(parser, allow_pattern_params=allow_pattern_params)
                except Namel3ssError as err:
                    raise Namel3ssError(
                        "Preview must be true or false",
                        line=err.line,
                        column=err.column,
                    ) from err
                if parser._match("NEWLINE"):
                    continue
                continue
            raise Namel3ssError(
                f"Unknown upload setting '{entry_tok.value}'",
                line=entry_tok.line,
                column=entry_tok.column,
            )
        parser._expect("DEDENT", "Expected end of upload block")
    else:
        visibility_rule = _parse_visibility_rule_block(parser, allow_pattern_params=allow_pattern_params)
    _validate_visibility_combo(visibility, visibility_rule, line=tok.line, column=tok.column)
    return ast.UploadItem(
        name=name,
        accept=accept,
        multiple=multiple,
        required=required,
        label=label,
        preview=preview,
        visibility=visibility,
        visibility_rule=visibility_rule,
        show_when=show_when,
        debug_only=debug_only,
        line=tok.line,
        column=tok.column,
    )


def _parse_upload_accept_list(parser, *, line: int, column: int) -> list[str]:
    accept: list[str] = []
    while True:
        tok = parser._current()
        if tok.type != "STRING":
            break
        raw_value = tok.value
        parser._advance()
        parts = [entry.strip() for entry in raw_value.split(",")]
        if not parts or any(entry == "" for entry in parts):
            raise Namel3ssError(
                "Upload accept entries must be valid MIME types or extensions",
                line=tok.line,
                column=tok.column,
            )
        for entry in parts:
            if not _is_valid_upload_accept(entry):
                raise Namel3ssError(
                    "Upload accept entries must be valid MIME types or extensions",
                    line=tok.line,
                    column=tok.column,
                )
            accept.append(entry)
        if not parser._match("COMMA"):
            break
    if not accept:
        raise Namel3ssError("Upload accept list must include at least one value", line=line, column=column)
    return accept


def _is_valid_upload_accept(value: str) -> bool:
    if "/" in value:
        return bool(_MIME_TYPE_RE.match(value))
    cleaned = value[1:] if value.startswith(".") else value
    return bool(_MIME_EXTENSION_RE.match(cleaned))


__all__ = ["parse_upload_item"]
