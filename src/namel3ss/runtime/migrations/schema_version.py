from __future__ import annotations


STATE_SCHEMA_VERSION = "state_schema@1"
MIGRATION_STATUS_SCHEMA_VERSION = "migration_status@1"


def normalize_state_schema_version(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return STATE_SCHEMA_VERSION
    return text


__all__ = [
    "MIGRATION_STATUS_SCHEMA_VERSION",
    "STATE_SCHEMA_VERSION",
    "normalize_state_schema_version",
]
