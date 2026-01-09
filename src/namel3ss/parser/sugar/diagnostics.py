from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message


def expected_phrase_error(tok, *, phrase: str, example: str) -> Namel3ssError:
    return Namel3ssError(
        build_guidance_message(
            what=f"Expected '{phrase}'.",
            why="English-first sugar uses fixed phrases to stay deterministic.",
            fix=f"Use the exact phrase '{phrase}'.",
            example=example,
        ),
        line=tok.line,
        column=tok.column,
    )


def expected_block_error(tok, *, label: str, example: str) -> Namel3ssError:
    return Namel3ssError(
        build_guidance_message(
            what=f"{label} block is missing.",
            why="This sugar form requires an indented block.",
            fix=f"Add an indented block after {label.lower()}.",
            example=example,
        ),
        line=tok.line,
        column=tok.column,
    )


def expected_value_error(tok, *, label: str, example: str) -> Namel3ssError:
    return Namel3ssError(
        build_guidance_message(
            what=f"{label} is missing.",
            why="This sugar form requires a value to stay deterministic.",
            fix=f"Add the {label.lower()}.",
            example=example,
        ),
        line=tok.line,
        column=tok.column,
    )


__all__ = ["expected_block_error", "expected_phrase_error", "expected_value_error"]
