from __future__ import annotations

from pathlib import Path

# Phase 0 freeze rules for tests.
# These constants define what counts as a breaking change in frozen outputs.

PHASE0_ROOT = Path("tests/golden/core_examples")
PARSER_GOLDEN_DIR = PHASE0_ROOT / "parser"
IR_GOLDEN_DIR = PHASE0_ROOT / "ir"
RUNTIME_GOLDEN_DIR = PHASE0_ROOT / "runtime"

BRACKET_CHARS = ("(", ")", "[", "]", "{", "}")
HUMAN_TEXT_KEYS = ("what", "because")

NONDETERMINISTIC_KEYS = (
    "timestamp",
    "duration_ms",
    "call_id",
    "tool_call_id",
    "error_id",
    "started_at",
    "ended_at",
)

PATH_KEYS = ("project_root", "app_path", "path")

NORMALIZED_VALUE = "<normalized>"


def has_bracket_chars(text: str) -> bool:
    return any(char in text for char in BRACKET_CHARS)


__all__ = [
    "BRACKET_CHARS",
    "HUMAN_TEXT_KEYS",
    "IR_GOLDEN_DIR",
    "NONDETERMINISTIC_KEYS",
    "NORMALIZED_VALUE",
    "PARSER_GOLDEN_DIR",
    "PATH_KEYS",
    "PHASE0_ROOT",
    "RUNTIME_GOLDEN_DIR",
    "has_bracket_chars",
]
