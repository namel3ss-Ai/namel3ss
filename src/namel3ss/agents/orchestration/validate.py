from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MergeValidator:
    require_keys: list[str]
    require_non_empty: bool


def validate_candidate(output: object, validator: MergeValidator) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if validator.require_keys:
        if not isinstance(output, dict):
            reasons.append("Output is not a map for required keys.")
        else:
            for key in validator.require_keys:
                if key not in output or output.get(key) in {None, ""}:
                    reasons.append(f"Missing required key '{key}'.")
    if validator.require_non_empty:
        text = None
        if isinstance(output, dict):
            text = output.get("text")
        elif isinstance(output, str):
            text = output
        if not isinstance(text, str) or not text.strip():
            reasons.append("Text output is empty.")
    return (len(reasons) == 0), reasons


__all__ = ["MergeValidator", "validate_candidate"]
