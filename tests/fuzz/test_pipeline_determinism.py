from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.contract import build_error_entry
from namel3ss.lexer.lexer import Lexer
from namel3ss.parser.core import Parser
from namel3ss.parser.sugar.lower import lower_program as lower_sugar_program
from tests.spec_freeze.helpers.ast_dump import dump_ast


_ALPHABET = (
    "abcdefghijklmnopqrstuvwxyz"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "0123456789"
    "_ \n:\"#-"
)


def _lcg(seed: int):
    value = seed & 0xFFFFFFFF
    while True:
        value = (value * 1664525 + 1013904223) & 0xFFFFFFFF
        yield value


def _generate_source(seed: int, length: int) -> str:
    rng = _lcg(seed)
    chars = [_ALPHABET[next(rng) % len(_ALPHABET)] for _ in range(length)]
    return "".join(chars)


def _dump_tokens(tokens):
    return [
        {
            "type": tok.type,
            "value": tok.value,
            "line": tok.line,
            "column": tok.column,
            "escaped": tok.escaped,
        }
        for tok in tokens
        if tok.type != "EOF"
    ]


def _run_pipeline(source: str) -> dict:
    try:
        tokens = Lexer(source).tokenize()
    except Namel3ssError as err:
        return {
            "tokens": [],
            "ast": None,
            "error": _error_entry(err),
        }
    parser = Parser(tokens, allow_legacy_type_aliases=True, allow_capsule=False, require_spec=False)
    try:
        program = parser._parse_program()
        program = lower_sugar_program(program)
        parser._expect("EOF")
        return {
            "tokens": _dump_tokens(tokens),
            "ast": dump_ast(program),
            "error": None,
        }
    except Namel3ssError as err:
        return {
            "tokens": _dump_tokens(tokens),
            "ast": None,
            "error": _error_entry(err),
        }


def _error_entry(error: Namel3ssError) -> dict:
    return build_error_entry(error=error, error_payload=None, error_pack=None)


def test_pipeline_determinism_for_seeded_inputs() -> None:
    seeds = [1, 7, 21, 42, 99]
    lengths = [0, 8, 32, 96]
    sources = [
        "",
        "\n",
        "  \n",
        'spec is "1.0"\n\nflow "demo":\n  return 1\n',
    ]
    for seed in seeds:
        for length in lengths:
            sources.append(_generate_source(seed, length))
    for source in sources:
        first = _run_pipeline(source)
        second = _run_pipeline(source)
        assert first == second
