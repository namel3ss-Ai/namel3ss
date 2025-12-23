from __future__ import annotations

from namel3ss.secrets import collect_secret_values, redact_text


def redact_cli_text(text: str) -> str:
    return redact_text(text, collect_secret_values())


__all__ = ["redact_cli_text"]
