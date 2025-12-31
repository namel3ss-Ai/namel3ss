from __future__ import annotations

import re

from namel3ss.cli.redaction import redact_cli_text


_BRACKET_TRANS = str.maketrans("", "", "[]{}()")
_FIRST_RUN_REPLACEMENTS = {
    "engine target": "execution environment",
    "proofs": "run summaries",
    "proof": "run summary",
    "capabilities": "permissions",
    "capability": "permission",
    "contract": "application definition",
    "capsules": "modules",
    "capsule": "module",
    "packs": "packages",
    "pack": "package",
    "boundary": "system area",
    "governance": "policy",
    "spec": "app format",
    "ir": "program format",
}
_FIRST_RUN_PATTERNS = [
    (re.compile(rf"\b{re.escape(key)}\b", re.IGNORECASE), value)
    for key, value in sorted(_FIRST_RUN_REPLACEMENTS.items(), key=lambda item: -len(item[0]))
]


def normalize_cli_text(text: str) -> str:
    return text.translate(_BRACKET_TRANS)


def prepare_cli_text(text: str) -> str:
    return normalize_cli_text(redact_cli_text(text))


def prepare_first_run_text(text: str) -> str:
    sanitized = redact_cli_text(text)
    for pattern, replacement in _FIRST_RUN_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)
    return normalize_cli_text(sanitized)


__all__ = ["normalize_cli_text", "prepare_cli_text", "prepare_first_run_text"]
