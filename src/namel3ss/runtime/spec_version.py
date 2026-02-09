from __future__ import annotations


NAMEL3SS_SPEC_VERSION = "namel3ss-spec@1"
RUNTIME_SPEC_VERSION = "runtime-spec@1"


def apply_runtime_spec_versions(payload: dict[str, object]) -> dict[str, object]:
    payload.setdefault("spec_version", NAMEL3SS_SPEC_VERSION)
    payload.setdefault("runtime_spec_version", RUNTIME_SPEC_VERSION)
    return payload


__all__ = [
    "NAMEL3SS_SPEC_VERSION",
    "RUNTIME_SPEC_VERSION",
    "apply_runtime_spec_versions",
]
