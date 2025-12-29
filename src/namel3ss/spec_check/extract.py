from __future__ import annotations

from namel3ss.ast import nodes as ast
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.lexer.tokens import Token


def extract_declared_spec(program_or_tokens) -> str:
    if isinstance(program_or_tokens, ast.Program):
        spec = getattr(program_or_tokens, "spec_version", None)
        if spec:
            return str(spec)
        raise _missing_spec_error()
    if isinstance(program_or_tokens, list) and all(isinstance(tok, Token) for tok in program_or_tokens):
        return _extract_from_tokens(program_or_tokens)
    raise _missing_spec_error()


def _extract_from_tokens(tokens: list[Token]) -> str:
    for idx, tok in enumerate(tokens):
        if tok.type != "SPEC":
            continue
        next_tok = tokens[idx + 1] if idx + 1 < len(tokens) else None
        value_tok = tokens[idx + 2] if idx + 2 < len(tokens) else None
        if next_tok and next_tok.type == "IS" and value_tok and value_tok.type == "STRING":
            value = str(value_tok.value or "").strip()
            if value:
                return value
    raise _missing_spec_error()


def _missing_spec_error() -> Namel3ssError:
    return Namel3ssError(
        build_guidance_message(
            what="Spec declaration is missing.",
            why="Every program must declare the spec version at the root.",
            fix='Add a spec declaration at the top of the file.',
            example='spec is "1.0"',
        )
    )


__all__ = ["extract_declared_spec"]
