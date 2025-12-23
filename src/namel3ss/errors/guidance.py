from __future__ import annotations


def build_guidance_message(*, what: str, why: str, fix: str, example: str) -> str:
    """Compose a short, skimmable guidance message."""
    return "\n".join(
        [
            f"What happened: {what}",
            f"Why: {why}",
            f"Fix: {fix}",
            f"Example: {example}",
        ]
    )
