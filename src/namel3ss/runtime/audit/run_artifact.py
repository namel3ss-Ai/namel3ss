from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Mapping, Sequence

from namel3ss.determinism import canonical_json_dumps
from namel3ss.observability.scrub import scrub_payload
from namel3ss.runtime.capabilities.contract_fields import extract_capability_usage


RUN_ARTIFACT_SCHEMA_VERSION = "run_artifact@1"

_VOLATILE_KEYS = {
    "call_id",
    "contract_warnings",
    "duration_ms",
    "generated_at",
    "hash",
    "revision",
    "time",
    "time_end",
    "time_start",
    "timestamp",
    "trace_id",
}


def build_run_artifact(
    *,
    response: Mapping[str, object] | None,
    app_path: str | Path | None,
    source: str | None,
    flow_name: str | None,
    action_id: str | None,
    input_payload: Mapping[str, object] | None,
    state_snapshot: Mapping[str, object] | None,
    provider_name: str | None,
    model_name: str | None,
    project_root: str | Path | None,
    secret_values: Sequence[str] | None = None,
) -> dict[str, object]:
    response_map = dict(response) if isinstance(response, Mapping) else {}
    state_map = _mapping_or_empty(state_snapshot) or _mapping_or_empty(response_map.get("state"))
    result_map = _mapping_or_empty(response_map.get("result"))
    retrieval_map = _extract_retrieval_bundle(result_map, state_map)
    prompt_map = _extract_prompt(result_map, response_map.get("traces"))
    runtime_errors = _runtime_errors(response_map)
    capabilities_enabled = _normalize_capability_packs(response_map.get("capabilities_enabled"))
    capability_versions = _normalize_capability_versions(response_map.get("capability_versions"))
    capability_usage = _normalize_capability_usage(response_map.get("capability_usage"))
    if not capability_usage:
        capability_usage = extract_capability_usage(response_map)

    app_name = _app_name(app_path)
    source_hash = _hash_text(source)
    entrypoint = _entrypoint(flow_name=flow_name, action_id=action_id)
    program_identity = {
        "app_name": app_name,
        "app_hash": source_hash or _hash_text(f"{app_name}:{entrypoint}"),
        "entrypoint": entrypoint,
        "flow_name": str(flow_name or ""),
        "action_id": str(action_id or ""),
    }

    artifact: dict[str, object] = {
        "schema_version": RUN_ARTIFACT_SCHEMA_VERSION,
        "program": program_identity,
        "inputs": {
            "payload": _mapping_or_empty(input_payload),
            "state": state_map,
        },
        "ingestion_artifacts": _mapping_or_empty(state_map.get("ingestion")),
        "retrieval_plan": _mapping_or_empty(retrieval_map.get("retrieval_plan")),
        "retrieval_trace": _list_of_maps(retrieval_map.get("retrieval_trace")),
        "trust_score_details": _mapping_or_empty(retrieval_map.get("trust_score_details")),
        "prompt": prompt_map,
        "model_config": {
            "provider": str(provider_name or ""),
            "model": str(model_name or ""),
        },
        "capabilities_enabled": capabilities_enabled,
        "capability_versions": capability_versions,
        "capability_usage": capability_usage,
        "output": result_map,
        "runtime_errors": runtime_errors,
    }
    artifact["checksums"] = _build_checksums(artifact)
    scrubbed = scrub_payload(
        artifact,
        secret_values=secret_values or [],
        project_root=project_root,
        app_path=app_path,
    )
    normalized = normalize_run_artifact(scrubbed)
    normalized["run_id"] = compute_run_id(normalized)
    return normalized


def normalize_run_artifact(value: object) -> dict[str, object]:
    if not isinstance(value, Mapping):
        return {}
    stripped = _strip_volatile(value)
    return _stable_json_value(stripped) if isinstance(_stable_json_value(stripped), dict) else {}


def compute_run_id(artifact: Mapping[str, object]) -> str:
    payload = _without_keys(artifact, {"run_id"})
    canonical = canonical_json_dumps(payload, pretty=False, drop_run_keys=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def compute_integrity_hash(artifact: Mapping[str, object]) -> str:
    canonical = canonical_json_dumps(_stable_json_value(dict(artifact)), pretty=False, drop_run_keys=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _extract_retrieval_bundle(
    result_map: Mapping[str, object],
    state_map: Mapping[str, object],
) -> dict[str, object]:
    retrieval = _mapping_or_empty(result_map.get("retrieval"))
    if retrieval:
        return retrieval
    state_retrieval = _mapping_or_empty(state_map.get("retrieval"))
    return state_retrieval


def _extract_prompt(result_map: Mapping[str, object], traces: object) -> dict[str, object]:
    prompt_text = _string(result_map.get("prompt")) or _string(result_map.get("answer_prompt"))
    prompt_hash = _string(result_map.get("prompt_hash"))
    if not prompt_hash and prompt_text:
        prompt_hash = _hash_text(prompt_text)
    trace_prompt_hash = _trace_prompt_hash(traces)
    if not prompt_hash and trace_prompt_hash:
        prompt_hash = trace_prompt_hash
    return {
        "text": prompt_text,
        "hash": prompt_hash,
    }


def _trace_prompt_hash(traces: object) -> str:
    if not isinstance(traces, list):
        return ""
    for trace in traces:
        if not isinstance(trace, Mapping):
            continue
        trace_type = _string(trace.get("type"))
        if trace_type not in {"answer_validation", "answer_explain"}:
            continue
        prompt_hash = _string(trace.get("prompt_hash"))
        if prompt_hash:
            return prompt_hash
    return ""


def _runtime_errors(response_map: Mapping[str, object]) -> list[dict[str, str]]:
    errors = _list_of_maps(response_map.get("runtime_errors"))
    if errors:
        normalized = [_normalize_runtime_error(entry) for entry in errors]
        return [entry for entry in normalized if entry]
    primary = _mapping_or_empty(response_map.get("runtime_error"))
    if primary:
        normalized = _normalize_runtime_error(primary)
        return [normalized] if normalized else []
    return []


def _normalize_runtime_error(value: Mapping[str, object]) -> dict[str, str]:
    category = _string(value.get("category"))
    message = _string(value.get("message"))
    hint = _string(value.get("hint"))
    origin = _string(value.get("origin"))
    stable_code = _string(value.get("stable_code"))
    if not (category and message and hint and origin and stable_code):
        return {}
    return {
        "category": category,
        "message": message,
        "hint": hint,
        "origin": origin,
        "stable_code": stable_code,
    }


def _build_checksums(artifact: Mapping[str, object]) -> dict[str, str]:
    inputs = _mapping_or_empty(artifact.get("inputs"))
    retrieval_trace = artifact.get("retrieval_trace")
    prompt = _mapping_or_empty(artifact.get("prompt"))
    output = artifact.get("output")
    prompt_hash = _string(prompt.get("hash"))
    if not prompt_hash:
        prompt_text = _string(prompt.get("text"))
        prompt_hash = _hash_text(prompt_text) if prompt_text else ""
    capability_usage = artifact.get("capability_usage")
    return {
        "inputs_hash": compute_component_hash(inputs),
        "retrieval_trace_hash": compute_component_hash(retrieval_trace),
        "prompt_hash": prompt_hash,
        "capability_usage_hash": compute_component_hash(capability_usage),
        "output_hash": compute_component_hash(output),
    }


def _app_name(app_path: str | Path | None) -> str:
    if not app_path:
        return ""
    try:
        return Path(app_path).name
    except Exception:
        return str(app_path)


def _entrypoint(*, flow_name: str | None, action_id: str | None) -> str:
    flow = str(flow_name or "").strip()
    if flow:
        return f"flow:{flow}"
    action = str(action_id or "").strip()
    if action:
        return f"action:{action}"
    return "runtime"


def _strip_volatile(value: object) -> object:
    if isinstance(value, Mapping):
        output: dict[str, object] = {}
        for key in sorted(value.keys(), key=str):
            text_key = str(key)
            if text_key in _VOLATILE_KEYS:
                continue
            output[text_key] = _strip_volatile(value[key])
        return output
    if isinstance(value, list):
        return [_strip_volatile(item) for item in value]
    return value


def _stable_json_value(value: object) -> object:
    if isinstance(value, Mapping):
        output: dict[str, object] = {}
        for key in sorted(value.keys(), key=str):
            output[str(key)] = _stable_json_value(value[key])
        return output
    if isinstance(value, list):
        return [_stable_json_value(item) for item in value]
    if isinstance(value, tuple):
        return [_stable_json_value(item) for item in value]
    if isinstance(value, set):
        return [_stable_json_value(item) for item in sorted(value, key=str)]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _without_keys(value: Mapping[str, object], keys: set[str]) -> dict[str, object]:
    output: dict[str, object] = {}
    for key in sorted(value.keys(), key=str):
        text_key = str(key)
        if text_key in keys:
            continue
        output[text_key] = value[key]
    return output


def _mapping_or_empty(value: object) -> dict[str, object]:
    if isinstance(value, Mapping):
        return {str(key): value[key] for key in value.keys()}
    return {}


def _list_of_maps(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    output: list[dict[str, object]] = []
    for item in value:
        if isinstance(item, Mapping):
            output.append({str(key): item[key] for key in item.keys()})
    return output


def _normalize_capability_packs(value: object) -> list[dict[str, object]]:
    packs = _list_of_maps(value)
    normalized: list[dict[str, object]] = []
    seen: set[str] = set()
    for entry in packs:
        name = _string(entry.get("name"))
        version = _string(entry.get("version"))
        if not name or not version:
            continue
        key = f"{name}:{version}"
        if key in seen:
            continue
        seen.add(key)
        normalized.append(
            {
                "name": name,
                "version": version,
                "provided_actions": _sorted_string_list(entry.get("provided_actions")),
                "required_permissions": _sorted_string_list(entry.get("required_permissions")),
                "runtime_bindings": _mapping_or_empty(entry.get("runtime_bindings")),
                "effect_capabilities": _sorted_string_list(entry.get("effect_capabilities")),
                "contract_version": _string(entry.get("contract_version")),
                "purity": _string(entry.get("purity")),
                "replay_mode": _string(entry.get("replay_mode")),
            }
        )
    normalized.sort(key=lambda item: (str(item.get("name") or ""), str(item.get("version") or "")))
    return normalized


def _normalize_capability_versions(value: object) -> dict[str, str]:
    if not isinstance(value, Mapping):
        return {}
    versions: dict[str, str] = {}
    for key in sorted(value.keys(), key=str):
        name = _string(key)
        version = _string(value.get(key))
        if not name or not version:
            continue
        versions[name] = version
    return versions


def _normalize_capability_usage(value: object) -> list[dict[str, object]]:
    entries = _list_of_maps(value)
    normalized: list[dict[str, object]] = []
    seen: set[str] = set()
    for entry in entries:
        pack_name = _string(entry.get("pack_name"))
        pack_version = _string(entry.get("pack_version"))
        action = _string(entry.get("action"))
        capability = _string(entry.get("capability"))
        status = _string(entry.get("status"))
        if not (pack_name and pack_version and action and capability and status):
            continue
        key = f"{pack_name}:{pack_version}:{action}:{capability}:{status}"
        if key in seen:
            continue
        seen.add(key)
        normalized.append(
            {
                "pack_name": pack_name,
                "pack_version": pack_version,
                "action": action,
                "capability": capability,
                "status": status,
                "reason": _string(entry.get("reason")),
                "purity": _string(entry.get("purity")),
                "replay_mode": _string(entry.get("replay_mode")),
                "required_permissions": _sorted_string_list(entry.get("required_permissions")),
            }
        )
    normalized.sort(
        key=lambda item: (
            str(item.get("pack_name") or ""),
            str(item.get("action") or ""),
            str(item.get("capability") or ""),
            str(item.get("status") or ""),
        )
    )
    return normalized


def _sorted_string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    deduped: dict[str, None] = {}
    for item in value:
        text = _string(item)
        if text:
            deduped[text] = None
    return sorted(deduped.keys())


def _string(value: object) -> str:
    if isinstance(value, str):
        return value.strip()
    return ""


def _hash_text(value: str | None) -> str:
    text = str(value or "")
    if not text:
        return ""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def compute_component_hash(value: object) -> str:
    canonical = canonical_json_dumps(_stable_json_value(value), pretty=False, drop_run_keys=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


__all__ = [
    "RUN_ARTIFACT_SCHEMA_VERSION",
    "build_run_artifact",
    "compute_component_hash",
    "compute_integrity_hash",
    "compute_run_id",
    "normalize_run_artifact",
]
