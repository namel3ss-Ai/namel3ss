from __future__ import annotations

from dataclasses import dataclass

from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.capabilities.model import CapabilityCheck


REASON_GUARANTEE_ALLOWED = "guarantee_allowed"
REASON_GUARANTEE_BLOCKED = "guarantee_blocked"
REASON_SECRETS_BLOCKED = "secrets_blocked"
REASON_SECRETS_ALLOWED = "secrets_allowed"
REASON_COVERAGE_MISSING = "coverage_missing"


@dataclass(frozen=True)
class CapabilityViolation(Exception):
    message: str
    check: CapabilityCheck

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.message


def build_block_message(*, tool_name: str, action: str, why: str, example: str) -> str:
    return build_guidance_message(
        what=f'Tool "{tool_name}" {action}.',
        why=why,
        fix="Remove the restriction or choose a tool that does not need the capability.",
        example=example,
    )


__all__ = [
    "CapabilityViolation",
    "REASON_COVERAGE_MISSING",
    "REASON_GUARANTEE_ALLOWED",
    "REASON_GUARANTEE_BLOCKED",
    "REASON_SECRETS_BLOCKED",
    "REASON_SECRETS_ALLOWED",
    "build_block_message",
]
