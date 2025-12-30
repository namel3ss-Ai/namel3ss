from __future__ import annotations

from namel3ss.cli.redaction import redact_cli_text


_BRACKET_TRANS = str.maketrans("", "", "[]{}()")


def normalize_cli_text(text: str) -> str:
    return text.translate(_BRACKET_TRANS)


def prepare_cli_text(text: str) -> str:
    return normalize_cli_text(redact_cli_text(text))


__all__ = ["normalize_cli_text", "prepare_cli_text"]
