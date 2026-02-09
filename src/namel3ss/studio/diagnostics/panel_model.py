from __future__ import annotations

from collections.abc import Mapping, Sequence

from namel3ss.runtime.audit.replay_engine import replay_run_artifact


STUDIO_DIAGNOSTICS_SCHEMA_VERSION = "studio_diagnostics@1"

_SEVERITY_ORDER = {
    "error": 0,
    "warn": 1,
    "info": 2,
}


def build_diagnostics_panel_payload(
    *,
    manifest: Mapping[str, object] | None,
    state_snapshot: Mapping[str, object] | None,
    runtime_errors: Sequence[Mapping[str, object]] | None,
    run_artifact: Mapping[str, object] | None,
) -> dict[str, object]:
    entries: list[dict[str, object]] = []
    entries.extend(_runtime_error_entries(runtime_errors, manifest=manifest))
    entries.extend(_ingestion_entries(state_snapshot))
    entries.extend(_contract_warning_entries(manifest))
    entries.extend(_capability_entries(manifest))
    entries.extend(_audit_entries(run_artifact))
    entries.sort(key=_entry_sort_key)
    summary = {
        "error": len([item for item in entries if item.get("severity") == "error"]),
        "warn": len([item for item in entries if item.get("severity") == "warn"]),
        "info": len([item for item in entries if item.get("severity") == "info"]),
    }
    return {
        "schema_version": STUDIO_DIAGNOSTICS_SCHEMA_VERSION,
        "entries": entries,
        "summary": summary,
    }


def _runtime_error_entries(
    runtime_errors: Sequence[Mapping[str, object]] | None,
    *,
    manifest: Mapping[str, object] | None,
) -> list[dict[str, object]]:
    values = list(runtime_errors or [])
    manifest_errors = _list_of_maps(_mapping_or_empty(manifest).get("runtime_errors"))
    if not values and manifest_errors:
        values = manifest_errors
    entries: list[dict[str, object]] = []
    seen: set[str] = set()
    for item in values:
        category = _text(item.get("category"))
        message = _text(item.get("message"))
        hint = _text(item.get("hint"))
        origin = _text(item.get("origin")) or "runtime"
        stable_code = _text(item.get("stable_code"))
        if not category or not message or not stable_code:
            continue
        if stable_code in seen:
            continue
        seen.add(stable_code)
        severity = "warn" if category in {"provider_mock_active", "provider_misconfigured"} else "error"
        entries.append(
            {
                "severity": severity,
                "source": "runtime",
                "category": category,
                "message": message,
                "hint": hint,
                "stable_code": stable_code,
                "origin": origin,
            }
        )
    return entries


def _ingestion_entries(state_snapshot: Mapping[str, object] | None) -> list[dict[str, object]]:
    state = _mapping_or_empty(state_snapshot)
    ingestion = _mapping_or_empty(state.get("ingestion"))
    if not ingestion:
        return []
    entries: list[dict[str, object]] = []
    for upload_id in sorted(ingestion.keys()):
        report = _mapping_or_empty(ingestion.get(upload_id))
        status = _text(report.get("status"))
        if status not in {"warn", "block"}:
            continue
        severity = "error" if status == "block" else "warn"
        reason_details = _list_of_maps(report.get("reason_details"))
        reasons = _list_of_strings(report.get("reasons"))
        if not reason_details:
            reason_details = [{"code": code, "message": code, "remediation": ""} for code in reasons]
        for index, detail in enumerate(reason_details):
            code = _text(detail.get("code")) or f"reason_{index + 1}"
            message = _text(detail.get("message")) or code
            remediation = _text(detail.get("remediation"))
            entries.append(
                {
                    "severity": severity,
                    "source": f"state.ingestion.{upload_id}",
                    "category": "ingestion",
                    "message": message,
                    "hint": remediation,
                    "stable_code": f"ingestion.{upload_id}.{code}",
                    "origin": "ingestion",
                }
            )
    return entries


def _contract_warning_entries(manifest: Mapping[str, object] | None) -> list[dict[str, object]]:
    warnings = _list_of_maps(_mapping_or_empty(manifest).get("contract_warnings"))
    entries: list[dict[str, object]] = []
    for warning in warnings:
        code = _text(warning.get("code"))
        message = _text(warning.get("message"))
        path = _text(warning.get("path"))
        if not code or not message or not path:
            continue
        entries.append(
            {
                "severity": "warn",
                "source": path,
                "category": "contract_warning",
                "message": message,
                "hint": "Review contract schema and payload shape.",
                "stable_code": f"contract.{code}",
                "origin": "contract",
            }
        )
    return entries


def _capability_entries(manifest: Mapping[str, object] | None) -> list[dict[str, object]]:
    packs = _list_of_maps(_mapping_or_empty(manifest).get("capabilities_enabled"))
    if not packs:
        return []
    entries: list[dict[str, object]] = []
    for pack in packs:
        name = _text(pack.get("name"))
        version = _text(pack.get("version"))
        permissions = _list_of_strings(pack.get("required_permissions"))
        if not name or not version:
            continue
        entries.append(
            {
                "severity": "info",
                "source": "capabilities",
                "category": "capability",
                "message": f"Capability pack {name}@{version} enabled.",
                "hint": f"Permissions: {', '.join(permissions) if permissions else 'none'}",
                "stable_code": f"capability.{name}.{version}",
                "origin": "capability",
            }
        )
    return entries


def _audit_entries(run_artifact: Mapping[str, object] | None) -> list[dict[str, object]]:
    artifact = _mapping_or_empty(run_artifact)
    if not artifact:
        return []
    replay = replay_run_artifact(artifact)
    mismatches = _list_of_maps(replay.get("mismatches"))
    if mismatches:
        return [
            {
                "severity": "error",
                "source": "audit.replay",
                "category": "audit_replay",
                "message": f"Replay mismatch detected for {len(mismatches)} field(s).",
                "hint": "Inspect run_diff and replay mismatches before sharing this run.",
                "stable_code": "audit.replay.mismatch",
                "origin": "audit",
            }
        ]
    return [
        {
            "severity": "info",
            "source": "audit.replay",
            "category": "audit_replay",
            "message": "Replay checks passed for the latest run artifact.",
            "hint": "Artifact is deterministic and ready for inspection.",
            "stable_code": "audit.replay.ok",
            "origin": "audit",
        }
    ]


def _entry_sort_key(entry: Mapping[str, object]) -> tuple[object, ...]:
    severity = _text(entry.get("severity"))
    source = _text(entry.get("source"))
    stable_code = _text(entry.get("stable_code"))
    message = _text(entry.get("message"))
    return (_SEVERITY_ORDER.get(severity, 3), source, stable_code, message)


def _mapping_or_empty(value: object) -> dict[str, object]:
    if not isinstance(value, Mapping):
        return {}
    return {str(key): value[key] for key in value.keys()}


def _list_of_maps(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    output: list[dict[str, object]] = []
    for item in value:
        if isinstance(item, Mapping):
            output.append({str(key): item[key] for key in item.keys()})
    return output


def _list_of_strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    output: list[str] = []
    seen: set[str] = set()
    for item in value:
        text = _text(item)
        if not text or text in seen:
            continue
        seen.add(text)
        output.append(text)
    return output


def _text(value: object) -> str:
    if isinstance(value, str):
        return value.strip()
    return ""


__all__ = [
    "STUDIO_DIAGNOSTICS_SCHEMA_VERSION",
    "build_diagnostics_panel_payload",
]
