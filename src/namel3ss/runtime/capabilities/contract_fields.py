from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from namel3ss.config.model import AppConfig
from namel3ss.runtime.capabilities.pack_model import CapabilityPack
from namel3ss.runtime.capabilities.registry import (
    capability_payload_list,
    capability_versions_map,
    get_capability_pack,
    normalize_capability_permissions,
)
from namel3ss.runtime.capabilities.validation import (
    CapabilityPackRequest,
    parse_capability_pack_requests,
    validate_capability_packs,
)
from namel3ss.runtime.contracts.runtime_schema import RUNTIME_UI_CONTRACT_VERSION
from namel3ss.runtime.errors.normalize import merge_runtime_errors


@dataclass(frozen=True)
class CapabilityContractSnapshot:
    enabled_packs: tuple[CapabilityPack, ...]
    capabilities_enabled: list[dict[str, object]]
    capability_versions: dict[str, str]
    runtime_errors: tuple[dict[str, str], ...]
    strict: bool


def attach_capability_contract_fields(
    response: dict,
    *,
    program_ir: object | None,
    config: AppConfig | None,
    runtime_contract_version: str = RUNTIME_UI_CONTRACT_VERSION,
) -> dict:
    if not isinstance(response, dict):
        return response
    snapshot = build_capability_contract_snapshot(
        program_ir=program_ir,
        config=config,
        runtime_contract_version=runtime_contract_version,
    )
    response["capabilities_enabled"] = snapshot.capabilities_enabled
    response["capability_versions"] = snapshot.capability_versions

    ui_payload = response.get("ui")
    if isinstance(ui_payload, dict):
        ui_payload["capabilities_enabled"] = snapshot.capabilities_enabled
        ui_payload["capability_versions"] = snapshot.capability_versions
        if _ui_capabilities_visible(ui_payload):
            _inject_capabilities_viewer_elements(
                ui_payload,
                capabilities_enabled=snapshot.capabilities_enabled,
                capability_versions=snapshot.capability_versions,
            )

    if snapshot.runtime_errors:
        existing_errors = response.get("runtime_errors")
        merged = merge_runtime_errors(
            existing_errors if isinstance(existing_errors, list) else [],
            list(snapshot.runtime_errors),
        )
        if merged:
            response["runtime_errors"] = merged
            response["runtime_error"] = merged[0]
            if snapshot.strict:
                response["ok"] = False
                response["error"] = {"message": merged[0]["message"]}
    return response


def attach_capability_manifest_fields(
    manifest: dict,
    *,
    program_ir: object | None,
    config: AppConfig | None,
    runtime_contract_version: str = RUNTIME_UI_CONTRACT_VERSION,
) -> tuple[dict, tuple[dict[str, str], ...]]:
    if not isinstance(manifest, dict):
        return manifest, tuple()
    snapshot = build_capability_contract_snapshot(
        program_ir=program_ir,
        config=config,
        runtime_contract_version=runtime_contract_version,
    )
    manifest["capabilities_enabled"] = snapshot.capabilities_enabled
    manifest["capability_versions"] = snapshot.capability_versions
    if _ui_capabilities_visible(manifest):
        _inject_capabilities_viewer_elements(
            manifest,
            capabilities_enabled=snapshot.capabilities_enabled,
            capability_versions=snapshot.capability_versions,
        )
    return manifest, snapshot.runtime_errors


def build_capability_contract_snapshot(
    *,
    program_ir: object | None,
    config: AppConfig | None,
    runtime_contract_version: str,
) -> CapabilityContractSnapshot:
    permissions = normalize_capability_permissions(_program_capabilities(program_ir))
    requests = _request_capability_packs(config)
    validation = validate_capability_packs(
        permissions=permissions,
        runtime_contract_version=runtime_contract_version,
        requests=requests or None,
    )
    packs = tuple(sorted(validation.packs, key=lambda item: item.name))
    return CapabilityContractSnapshot(
        enabled_packs=packs,
        capabilities_enabled=capability_payload_list(packs),
        capability_versions=capability_versions_map(packs),
        runtime_errors=validation.diagnostics,
        strict=bool(requests),
    )


def extract_capability_usage(
    response: dict | None,
    *,
    enabled_packs: Iterable[CapabilityPack] | None = None,
) -> list[dict[str, object]]:
    response_map = response if isinstance(response, dict) else {}
    traces = _trace_items(response_map)
    packs = list(enabled_packs or _enabled_packs_from_payload(response_map.get("capabilities_enabled")))
    if not traces or not packs:
        return []
    by_effect: dict[str, list[CapabilityPack]] = {}
    for pack in packs:
        for capability in pack.effect_capabilities:
            by_effect.setdefault(capability, []).append(pack)
    usage: list[dict[str, object]] = []
    seen: set[str] = set()
    for trace in traces:
        trace_type = _text(trace.get("type"))
        if trace_type != "capability_check":
            continue
        capability = _text(trace.get("capability"))
        if not capability:
            continue
        matched_packs = sorted(by_effect.get(capability, []), key=lambda pack: pack.name)
        for pack in matched_packs:
            action = _text(trace.get("tool_name")) or capability
            status = "allowed" if trace.get("allowed") is True else "blocked"
            reason = _text(trace.get("reason")) or "capability_check"
            key = f"{pack.name}::{pack.version}::{action}::{capability}::{status}"
            if key in seen:
                continue
            seen.add(key)
            usage.append(
                {
                    "pack_name": pack.name,
                    "pack_version": pack.version,
                    "action": action,
                    "capability": capability,
                    "status": status,
                    "reason": reason,
                    "purity": pack.purity,
                    "replay_mode": pack.replay_mode,
                    "required_permissions": list(pack.required_permissions),
                }
            )
    usage.sort(
        key=lambda item: (
            str(item.get("pack_name") or ""),
            str(item.get("action") or ""),
            str(item.get("capability") or ""),
            str(item.get("status") or ""),
        )
    )
    return usage


def _enabled_packs_from_payload(value: object) -> tuple[CapabilityPack, ...]:
    if not isinstance(value, list):
        return tuple()
    names: list[str] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        name = _text(item.get("name"))
        if name:
            names.append(name)
    packs: list[CapabilityPack] = []
    for name in sorted(set(names)):
        pack = get_capability_pack(name)
        if pack is not None:
            packs.append(pack)
    return tuple(packs)


def _trace_items(response: dict) -> list[dict[str, object]]:
    traces = response.get("traces")
    if isinstance(traces, list):
        return [item for item in traces if isinstance(item, dict)]
    result = response.get("result")
    if isinstance(result, dict):
        nested = result.get("traces")
        if isinstance(nested, list):
            return [item for item in nested if isinstance(item, dict)]
    return []


def _request_capability_packs(config: AppConfig | None) -> tuple[CapabilityPackRequest, ...]:
    if config is None:
        return tuple()
    enabled = getattr(getattr(config, "tool_packs", None), "enabled_packs", None)
    if not isinstance(enabled, list):
        return tuple()
    return parse_capability_pack_requests(enabled)


def _program_capabilities(program_ir: object | None) -> tuple[str, ...]:
    values = getattr(program_ir, "capabilities", None)
    if not isinstance(values, tuple):
        return tuple()
    return tuple(value for value in values if isinstance(value, str))


def _ui_capabilities_visible(payload: dict) -> bool:
    mode = _text(payload.get("mode"))
    if mode == "studio":
        return True
    return bool(payload.get("diagnostics_enabled"))


def _inject_capabilities_viewer_elements(
    manifest: dict,
    *,
    capabilities_enabled: object,
    capability_versions: object,
) -> None:
    from namel3ss.ui.manifest.elements.capabilities_viewer import inject_capabilities_viewer_elements

    inject_capabilities_viewer_elements(
        manifest,
        capabilities_enabled=capabilities_enabled,
        capability_versions=capability_versions,
    )


def _text(value: object) -> str:
    if isinstance(value, str):
        return value.strip().lower()
    return ""


__all__ = [
    "CapabilityContractSnapshot",
    "attach_capability_contract_fields",
    "attach_capability_manifest_fields",
    "build_capability_contract_snapshot",
    "extract_capability_usage",
]
