from __future__ import annotations

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.capabilities.model import GUARANTEE_FIELDS


OVERRIDE_FIELDS = set(GUARANTEE_FIELDS) | {"secrets_allowed", "allow_unsafe_execution"}


def normalize_overrides(raw: object, *, label: str) -> dict[str, object]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise Namel3ssError(_invalid_override_message(label, "Overrides must be a mapping."))
    normalized: dict[str, object] = {}
    for key, value in raw.items():
        if not isinstance(key, str) or not key:
            raise Namel3ssError(_invalid_override_message(label, "Override keys must be strings."))
        if key not in OVERRIDE_FIELDS:
            raise Namel3ssError(_invalid_override_message(label, f"Unsupported override field '{key}'."))
        if key == "secrets_allowed":
            normalized[key] = _normalize_secrets(value, label)
            continue
        if key == "allow_unsafe_execution":
            if not isinstance(value, bool):
                raise Namel3ssError(_invalid_override_message(label, "allow_unsafe_execution must be true or false."))
            normalized[key] = value
            continue
        if not isinstance(value, bool):
            raise Namel3ssError(_invalid_override_message(label, f"{key} must be true or false."))
        normalized[key] = value
    return normalized


def _normalize_secrets(value: object, label: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise Namel3ssError(_invalid_override_message(label, "secrets_allowed must be a list of strings."))
    return sorted(dict.fromkeys(value))


def _invalid_override_message(label: str, reason: str) -> str:
    return build_guidance_message(
        what=f"Capability overrides for {label} are invalid.",
        why=reason,
        fix="Update capability_overrides in namel3ss.toml.",
        example='[capability_overrides]\\n"send email" = { no_network = true }',
    )


__all__ = ["normalize_overrides"]
