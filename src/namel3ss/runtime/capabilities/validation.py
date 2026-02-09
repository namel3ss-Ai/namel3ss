from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from namel3ss.runtime.capabilities.pack_model import CapabilityPack
from namel3ss.runtime.capabilities.registry import (
    capability_versions_map,
    get_capability_pack,
    resolve_enabled_capability_packs,
)
from namel3ss.runtime.errors.classification import build_runtime_error


@dataclass(frozen=True)
class CapabilityPackRequest:
    name: str
    version: str | None = None


@dataclass(frozen=True)
class CapabilityValidationResult:
    packs: tuple[CapabilityPack, ...]
    diagnostics: tuple[dict[str, str], ...]


def parse_capability_pack_requests(values: Iterable[str] | None) -> tuple[CapabilityPackRequest, ...]:
    requests: dict[str, CapabilityPackRequest] = {}
    for raw in values or ():
        if not isinstance(raw, str):
            continue
        text = raw.strip().lower()
        if not text.startswith("capability."):
            continue
        payload = text[len("capability.") :]
        if "@" in payload:
            name, version = payload.split("@", 1)
            version_text = version.strip() or None
        else:
            name = payload
            version_text = None
        name_text = name.strip()
        if not name_text:
            continue
        requests[name_text] = CapabilityPackRequest(name=name_text, version=version_text)
    return tuple(sorted(requests.values(), key=lambda item: item.name))


def validate_capability_packs(
    *,
    permissions: Iterable[str] | None,
    runtime_contract_version: str,
    requests: tuple[CapabilityPackRequest, ...] | None = None,
) -> CapabilityValidationResult:
    permission_set = set(_normalize_permissions(permissions))
    diagnostics: list[dict[str, str]] = []
    packs: list[CapabilityPack] = []

    if requests:
        for request in requests:
            pack = get_capability_pack(request.name)
            if pack is None:
                diagnostics.append(_unknown_capability_error(request.name))
                continue
            if request.version and request.version != pack.version:
                diagnostics.append(_version_mismatch_error(request.name, expected=pack.version, actual=request.version))
                continue
            packs.append(pack)
    else:
        packs.extend(resolve_enabled_capability_packs(permission_set))

    resolved: list[CapabilityPack] = []
    for pack in sorted(packs, key=lambda item: item.name):
        if pack.contract_version != runtime_contract_version:
            diagnostics.append(
                _contract_mismatch_error(
                    pack.name,
                    expected=runtime_contract_version,
                    actual=pack.contract_version,
                )
            )
            continue
        missing_permissions = sorted(set(pack.required_permissions) - permission_set)
        if missing_permissions:
            diagnostics.append(_missing_permission_error(pack.name, missing_permissions))
            continue
        resolved.append(pack)

    return CapabilityValidationResult(
        packs=tuple(resolved),
        diagnostics=tuple(_dedupe_diagnostics(diagnostics)),
    )


def capability_versions_from_result(result: CapabilityValidationResult) -> dict[str, str]:
    return capability_versions_map(result.packs)


def _normalize_permissions(values: Iterable[str] | None) -> tuple[str, ...]:
    deduped: dict[str, None] = {}
    for value in values or ():
        text = str(value or "").strip().lower()
        if text:
            deduped[text] = None
    return tuple(sorted(deduped))


def _dedupe_diagnostics(entries: list[dict[str, str]]) -> list[dict[str, str]]:
    deduped: dict[str, dict[str, str]] = {}
    for entry in entries:
        code = str(entry.get("stable_code") or "").strip()
        if not code:
            continue
        deduped.setdefault(code, entry)
    return [deduped[key] for key in sorted(deduped)]


def _unknown_capability_error(name: str) -> dict[str, str]:
    token = _slug(name)
    return build_runtime_error(
        "runtime_internal",
        message=f"Capability pack '{name}' is not registered.",
        hint="Use one of the built-in capability packs or remove the unknown request.",
        origin="runtime",
        stable_code=f"runtime.runtime_internal.capability_unknown.{token}",
    )


def _version_mismatch_error(name: str, *, expected: str, actual: str) -> dict[str, str]:
    token = _slug(name)
    return build_runtime_error(
        "runtime_internal",
        message=f"Capability pack '{name}' version mismatch: expected {expected}, got {actual}.",
        hint="Pin a supported capability pack version in config.",
        origin="runtime",
        stable_code=f"runtime.runtime_internal.capability_version_mismatch.{token}",
    )


def _contract_mismatch_error(name: str, *, expected: str, actual: str) -> dict[str, str]:
    token = _slug(name)
    return build_runtime_error(
        "runtime_internal",
        message=f"Capability pack '{name}' contract mismatch: expected {expected}, got {actual}.",
        hint="Upgrade the capability pack or runtime so contract versions match.",
        origin="runtime",
        stable_code=f"runtime.runtime_internal.capability_contract_mismatch.{token}",
    )


def _missing_permission_error(name: str, missing_permissions: list[str]) -> dict[str, str]:
    token = _slug(name)
    missing = ", ".join(missing_permissions)
    return build_runtime_error(
        "policy_denied",
        message=f"Capability pack '{name}' requires missing permissions: {missing}.",
        hint="Add the required capabilities to app.ai or remove the capability pack request.",
        origin="policy",
        stable_code=f"runtime.policy_denied.capability_permission.{token}",
    )


def _slug(value: str) -> str:
    token = "".join(ch if ch.isalnum() else "_" for ch in value.strip().lower())
    normalized = "_".join(part for part in token.split("_") if part)
    return normalized or "unknown"


__all__ = [
    "CapabilityPackRequest",
    "CapabilityValidationResult",
    "capability_versions_from_result",
    "parse_capability_pack_requests",
    "validate_capability_packs",
]
