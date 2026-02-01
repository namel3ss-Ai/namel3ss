from __future__ import annotations

from dataclasses import dataclass

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.contract import build_error_entry
from namel3ss.lexer.lexer import Lexer
from namel3ss.lexer.tokens import Token
from namel3ss.parser.core import Parser
from namel3ss.parser.sugar.lower import lower_program as lower_sugar_program


@dataclass(frozen=True)
class IncrementalEdit:
    start: int
    delete_len: int
    insert_text: str


@dataclass(frozen=True)
class IncrementalState:
    source: str
    tokens: list[Token]
    program: ast.Program | None
    error: dict | None


def full_parse_state(
    source: str,
    *,
    allow_legacy_type_aliases: bool = True,
    allow_capsule: bool = False,
    require_spec: bool = True,
    lower_sugar: bool = True,
) -> IncrementalState:
    try:
        tokens = Lexer(source).tokenize()
    except Namel3ssError as err:
        return IncrementalState(
            source=source,
            tokens=[],
            program=None,
            error=_error_entry(err),
        )
    program, error = _parse_tokens(
        tokens,
        allow_legacy_type_aliases=allow_legacy_type_aliases,
        allow_capsule=allow_capsule,
        require_spec=require_spec,
        lower_sugar=lower_sugar,
    )
    return IncrementalState(
        source=source,
        tokens=tokens,
        program=program,
        error=error,
    )


def incremental_parse(
    prev_state: IncrementalState,
    edit: IncrementalEdit,
    *,
    allow_legacy_type_aliases: bool = True,
    allow_capsule: bool = False,
    require_spec: bool = True,
    lower_sugar: bool = True,
) -> IncrementalState:
    next_source = _apply_edit(prev_state.source, edit)
    return full_parse_state(
        next_source,
        allow_legacy_type_aliases=allow_legacy_type_aliases,
        allow_capsule=allow_capsule,
        require_spec=require_spec,
        lower_sugar=lower_sugar,
    )


def _parse_tokens(
    tokens: list[Token],
    *,
    allow_legacy_type_aliases: bool,
    allow_capsule: bool,
    require_spec: bool,
    lower_sugar: bool,
) -> tuple[ast.Program | None, dict | None]:
    parser = Parser(
        tokens,
        allow_legacy_type_aliases=allow_legacy_type_aliases,
        allow_capsule=allow_capsule,
        require_spec=require_spec,
    )
    try:
        program = parser._parse_program()
        if lower_sugar:
            program = lower_sugar_program(program)
        parser._expect("EOF")
    except Namel3ssError as err:
        return None, _error_entry(err)
    return program, None


def _apply_edit(source: str, edit: IncrementalEdit) -> str:
    if edit.start < 0 or edit.start > len(source):
        raise ValueError("Edit start is out of bounds")
    if edit.delete_len < 0 or edit.start + edit.delete_len > len(source):
        raise ValueError("Edit delete length is out of bounds")
    return source[: edit.start] + edit.insert_text + source[edit.start + edit.delete_len :]


def _error_entry(error: Namel3ssError) -> dict:
    return build_error_entry(error=error, error_payload=None, error_pack=None)


__all__ = ["IncrementalEdit", "IncrementalState", "full_parse_state", "incremental_parse"]
