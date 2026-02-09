from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.parser.decl.type_reference import parse_type_reference


_UI_STATE_GRAMMAR = "ui_state must define one or more scopes: ephemeral, session, persistent."
_UI_STATE_SCOPE_GRAMMAR = "ui_state scopes must be one of: ephemeral, session, persistent."
_UI_STATE_FIELD_GRAMMAR = "ui_state fields must use: <key> is <type>."
_VALID_SCOPES = ("ephemeral", "session", "persistent")


def parse_ui_state_decl(parser) -> ast.UIStateDecl:
    header = parser._expect("IDENT", "Expected 'ui_state'")
    if header.value != "ui_state":
        raise Namel3ssError(_UI_STATE_GRAMMAR, line=header.line, column=header.column)
    parser._expect("COLON", "Expected ':' after ui_state")
    parser._expect("NEWLINE", "Expected newline after ui_state header")
    parser._expect("INDENT", "Expected indented ui_state block")
    scopes: dict[str, list[ast.UIStateField]] = {scope: [] for scope in _VALID_SCOPES}
    seen_scopes: set[str] = set()
    seen_keys: dict[str, str] = {}
    while parser._current().type != "DEDENT":
        if parser._match("NEWLINE"):
            continue
        scope_tok = parser._expect("IDENT", "Expected ui_state scope")
        scope = str(scope_tok.value or "")
        if scope not in _VALID_SCOPES:
            raise Namel3ssError(_UI_STATE_SCOPE_GRAMMAR, line=scope_tok.line, column=scope_tok.column)
        if scope in seen_scopes:
            raise Namel3ssError(
                f"ui_state scope '{scope}' is already declared.",
                line=scope_tok.line,
                column=scope_tok.column,
            )
        seen_scopes.add(scope)
        parser._expect("COLON", "Expected ':' after ui_state scope")
        parser._expect("NEWLINE", "Expected newline after ui_state scope")
        if not parser._match("INDENT"):
            raise Namel3ssError(
                f"ui_state scope '{scope}' must declare at least one state key.",
                line=scope_tok.line,
                column=scope_tok.column,
            )
        fields: list[ast.UIStateField] = []
        while parser._current().type != "DEDENT":
            if parser._match("NEWLINE"):
                continue
            field = _parse_ui_state_field(parser)
            duplicate_scope = seen_keys.get(field.key)
            if duplicate_scope is not None:
                raise Namel3ssError(
                    f"ui_state key '{field.key}' is already declared in scope '{duplicate_scope}'.",
                    line=field.line,
                    column=field.column,
                )
            seen_keys[field.key] = scope
            fields.append(field)
            parser._match("NEWLINE")
        parser._expect("DEDENT", "Expected end of ui_state scope block")
        if not fields:
            raise Namel3ssError(
                f"ui_state scope '{scope}' must declare at least one state key.",
                line=scope_tok.line,
                column=scope_tok.column,
            )
        scopes[scope] = fields
        parser._match("NEWLINE")
    parser._expect("DEDENT", "Expected end of ui_state block")
    while parser._match("NEWLINE"):
        continue
    if not seen_scopes:
        raise Namel3ssError(_UI_STATE_GRAMMAR, line=header.line, column=header.column)
    return ast.UIStateDecl(
        ephemeral=scopes["ephemeral"],
        session=scopes["session"],
        persistent=scopes["persistent"],
        line=header.line,
        column=header.column,
    )


def _parse_ui_state_field(parser) -> ast.UIStateField:
    key_tok = _parse_ui_state_key(parser)
    parser._expect("IS", "Expected 'is' after ui_state key")
    type_name, _alias, raw_type_name, _type_line, _type_column = parse_type_reference(parser)
    current = parser._current()
    if current.type not in {"NEWLINE", "DEDENT"}:
        raise Namel3ssError(_UI_STATE_FIELD_GRAMMAR, line=current.line, column=current.column)
    return ast.UIStateField(
        key=str(key_tok.value),
        type_name=type_name,
        raw_type_name=raw_type_name,
        line=key_tok.line,
        column=key_tok.column,
    )


def _parse_ui_state_key(parser):
    tok = parser._current()
    if tok.type in {"NEWLINE", "DEDENT", "COLON", "IS"}:
        raise Namel3ssError("Expected ui_state key", line=tok.line, column=tok.column)
    parser._advance()
    if not isinstance(tok.value, str) or not tok.value.strip():
        raise Namel3ssError("Expected ui_state key", line=tok.line, column=tok.column)
    return tok


__all__ = ["parse_ui_state_decl"]
