from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from typing import Mapping
from urllib.parse import unquote

from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.payload import build_error_payload
from namel3ss.runtime.contracts.runtime_schema import RUNTIME_UI_CONTRACT_VERSION
from namel3ss.runtime.errors.normalize import attach_runtime_error_payload
from namel3ss.runtime.spec_version import apply_runtime_spec_versions

HEADLESS_API_VERSION = "v1"
HEADLESS_API_PREFIX = f"/api/{HEADLESS_API_VERSION}"
SUPPORTED_HEADLESS_API_VERSIONS = (HEADLESS_API_VERSION,)


@dataclass(frozen=True)
class HeadlessRequestGate:
    ok: bool
    status: int = 200
    payload: dict | None = None
    headers: dict[str, str] | None = None


def is_versioned_api_path(path: str) -> bool:
    return str(path or "").startswith("/api/v")


def is_headless_ui_path(path: str) -> bool:
    normalized = _normalize_path(path)
    return normalized == f"{HEADLESS_API_PREFIX}/ui"


def headless_action_id(path: str) -> str | None:
    normalized = _normalize_path(path)
    prefix = f"{HEADLESS_API_PREFIX}/actions/"
    if not normalized.startswith(prefix):
        return None
    raw_action_id = normalized[len(prefix) :]
    if not raw_action_id:
        return None
    return unquote(raw_action_id)


def unsupported_version_payload() -> dict:
    payload = _headless_error_payload("Unsupported API version.", kind="engine")
    payload["supported_versions"] = list(SUPPORTED_HEADLESS_API_VERSIONS)
    payload = attach_runtime_error_payload(payload, status_code=404, endpoint="/api/v1")
    return _with_headless_contract(payload)


def normalize_api_token(value: object) -> str | None:
    if value is None:
        return None
    token = str(value).strip()
    return token or None


def normalize_cors_origins(value: object) -> tuple[str, ...]:
    if value is None:
        return tuple()
    if isinstance(value, str):
        return _parse_origins_text(value)
    if isinstance(value, (list, tuple)):
        merged: list[str] = []
        for item in value:
            if item is None:
                continue
            if isinstance(item, str):
                merged.extend(_parse_origins_text(item))
        return _dedupe(merged)
    return tuple()


def authorize_headless_request(
    *,
    path: str,
    headers: Mapping[str, object],
    headless: bool,
    api_token: object,
    cors_origins: object,
) -> HeadlessRequestGate:
    if not is_versioned_api_path(path):
        return HeadlessRequestGate(ok=True)
    if not _is_supported_headless_path(path):
        return HeadlessRequestGate(ok=False, status=404, payload=unsupported_version_payload())
    cors_gate = _authorize_origin(headers=headers, cors_origins=cors_origins)
    if not cors_gate.ok:
        return cors_gate
    if not headless:
        return HeadlessRequestGate(ok=True, headers=cors_gate.headers)
    expected_token = normalize_api_token(api_token)
    if expected_token is None:
        return HeadlessRequestGate(
            ok=False,
            status=401,
            payload=_headless_error_payload(
                "Headless API token is required for /api/v1 endpoints.",
                kind="authentication",
            ),
            headers=cors_gate.headers,
        )
    provided_token = _extract_request_token(headers)
    if provided_token is None:
        return HeadlessRequestGate(
            ok=False,
            status=401,
            payload=_headless_error_payload("API token is required.", kind="authentication"),
            headers=cors_gate.headers,
        )
    if not hmac.compare_digest(provided_token, expected_token):
        return HeadlessRequestGate(
            ok=False,
            status=401,
            payload=_headless_error_payload("Invalid API token.", kind="authentication"),
            headers=cors_gate.headers,
        )
    return HeadlessRequestGate(ok=True, headers=cors_gate.headers)


def authorize_headless_preflight(
    *,
    path: str,
    headers: Mapping[str, object],
    headless: bool,
    cors_origins: object,
) -> HeadlessRequestGate:
    if not is_versioned_api_path(path):
        return HeadlessRequestGate(ok=False, status=404, payload=_headless_error_payload("Not Found", kind="engine"))
    if not _is_supported_headless_path(path):
        return HeadlessRequestGate(ok=False, status=404, payload=unsupported_version_payload())
    cors_gate = _authorize_origin(headers=headers, cors_origins=cors_origins)
    if not cors_gate.ok:
        return cors_gate
    if not headless:
        return HeadlessRequestGate(ok=True, status=204, headers=cors_gate.headers or {})
    headers_map = dict(cors_gate.headers or {})
    headers_map["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    headers_map["Access-Control-Allow-Headers"] = "Authorization, Content-Type, X-API-Token"
    headers_map["Access-Control-Max-Age"] = "600"
    return HeadlessRequestGate(ok=True, status=204, headers=headers_map)


def query_flag(query: Mapping[str, list[str]], key: str) -> bool:
    values = query.get(key) or []
    if not values:
        return False
    token = str(values[0] or "").strip().lower()
    return token in {"1", "true", "yes", "on"}


def headless_ui_response_headers(
    payload: dict,
    *,
    include_state: bool,
    include_actions: bool,
) -> dict[str, str]:
    headers: dict[str, str] = {
        "Vary": "Authorization, X-API-Token, Origin",
    }
    if include_state or include_actions:
        headers["Cache-Control"] = "no-store"
    else:
        headers["Cache-Control"] = "private, max-age=0, must-revalidate"
    etag = headless_ui_etag(payload)
    if etag:
        headers["ETag"] = etag
    return headers


def headless_ui_etag(payload: dict) -> str | None:
    hash_value = payload.get("hash")
    if not isinstance(hash_value, str) or not hash_value.strip():
        return None
    return f'"sha256-{hash_value.strip()}"'


def request_etag_matches(headers: Mapping[str, object], etag: str) -> bool:
    normalized_target = _normalize_etag_token(etag)
    if normalized_target is None:
        return False
    for key, value in headers.items():
        if str(key).lower() != "if-none-match":
            continue
        if not isinstance(value, str):
            return False
        candidates = [token.strip() for token in value.split(",")]
        for candidate in candidates:
            normalized_candidate = _normalize_etag_token(candidate)
            if normalized_candidate == "*":
                return True
            if normalized_candidate is not None and normalized_candidate == normalized_target:
                return True
        return False
    return False


def normalize_headless_action_payload(body: object) -> tuple[dict | None, dict | None]:
    if not isinstance(body, dict):
        payload = _headless_error_payload("Body must be a JSON object", kind="engine")
        payload = attach_runtime_error_payload(payload, status_code=400, endpoint="/api/v1/actions")
        payload = _with_headless_contract(payload)
        return None, payload
    raw_payload = body.get("payload")
    if raw_payload is None:
        raw_payload = body.get("args")
    if raw_payload is None:
        raw_payload = {}
    if not isinstance(raw_payload, dict):
        payload = _headless_error_payload("Action args must be an object", kind="engine")
        payload = attach_runtime_error_payload(payload, status_code=400, endpoint="/api/v1/actions")
        payload = _with_headless_contract(payload)
        return None, payload
    return raw_payload, None


def build_manifest_hash(manifest: dict) -> str:
    payload = canonical_json_dumps(manifest, pretty=False, drop_run_keys=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def build_headless_ui_payload(
    *,
    manifest: dict,
    revision: str | None = None,
    state: dict | None = None,
    actions: dict | None = None,
) -> dict:
    if not isinstance(manifest, dict):
        return _headless_error_payload("Manifest payload is invalid", kind="engine")
    if manifest.get("ok") is False:
        payload = {
            "ok": False,
            "api_version": HEADLESS_API_VERSION,
            "contract_version": RUNTIME_UI_CONTRACT_VERSION,
            "error": manifest.get("error") if isinstance(manifest.get("error"), dict) else {"message": "Manifest request failed"},
        }
        if isinstance(revision, str) and revision:
            payload["revision"] = revision
        return _with_headless_contract(payload)
    payload = {
        "ok": True,
        "api_version": HEADLESS_API_VERSION,
        "contract_version": RUNTIME_UI_CONTRACT_VERSION,
        "manifest": manifest,
        "hash": build_manifest_hash(manifest),
    }
    if isinstance(revision, str) and revision:
        payload["revision"] = revision
    if isinstance(state, dict):
        payload["state"] = _with_headless_contract(dict(state))
    if isinstance(actions, dict):
        payload["actions"] = _with_headless_contract(dict(actions))
    capabilities_enabled = manifest.get("capabilities_enabled")
    if isinstance(capabilities_enabled, list):
        payload["capabilities_enabled"] = [entry for entry in capabilities_enabled if isinstance(entry, dict)]
    capability_versions = manifest.get("capability_versions")
    if isinstance(capability_versions, dict):
        payload["capability_versions"] = {
            str(key): str(value)
            for key, value in sorted(capability_versions.items(), key=lambda item: str(item[0]))
            if str(key).strip() and str(value).strip()
        }
    run_artifact = manifest.get("run_artifact")
    if isinstance(run_artifact, dict):
        payload["run_artifact"] = run_artifact
    persistence_backend = manifest.get("persistence_backend")
    if isinstance(persistence_backend, dict):
        payload["persistence_backend"] = persistence_backend
    state_schema_version = manifest.get("state_schema_version")
    if isinstance(state_schema_version, str) and state_schema_version:
        payload["state_schema_version"] = state_schema_version
    migration_status = manifest.get("migration_status")
    if isinstance(migration_status, dict):
        payload["migration_status"] = migration_status
    audit_bundle = manifest.get("audit_bundle")
    if isinstance(audit_bundle, dict):
        payload["audit_bundle"] = audit_bundle
    audit_policy_status = manifest.get("audit_policy_status")
    if isinstance(audit_policy_status, dict):
        payload["audit_policy_status"] = audit_policy_status
    return _with_headless_contract(payload)


def build_headless_action_payload(
    *,
    action_id: str,
    action_response: dict,
) -> tuple[dict, int]:
    if not isinstance(action_response, dict):
        payload = _headless_error_payload("Action response invalid", kind="engine")
        payload["action_id"] = action_id
        return _with_headless_contract(payload), 500
    ok = bool(action_response.get("ok", False))
    payload: dict[str, object] = {
        "ok": ok,
        "api_version": HEADLESS_API_VERSION,
        "contract_version": RUNTIME_UI_CONTRACT_VERSION,
        "action_id": action_id,
    }
    state_payload = action_response.get("state")
    if isinstance(state_payload, dict):
        payload["state"] = state_payload
    manifest_payload = action_response.get("ui")
    if isinstance(manifest_payload, dict):
        payload["manifest"] = manifest_payload
        payload["hash"] = build_manifest_hash(manifest_payload)
    messages = action_response.get("messages")
    if isinstance(messages, list):
        payload["messages"] = [entry for entry in messages if isinstance(entry, dict)]
    if "result" in action_response:
        payload["result"] = action_response.get("result")
    runtime_error = action_response.get("runtime_error")
    if isinstance(runtime_error, dict):
        payload["runtime_error"] = runtime_error
    runtime_errors = action_response.get("runtime_errors")
    if isinstance(runtime_errors, list):
        payload["runtime_errors"] = [entry for entry in runtime_errors if isinstance(entry, dict)]
    capabilities_enabled = action_response.get("capabilities_enabled")
    if isinstance(capabilities_enabled, list):
        payload["capabilities_enabled"] = [entry for entry in capabilities_enabled if isinstance(entry, dict)]
    capability_versions = action_response.get("capability_versions")
    if isinstance(capability_versions, dict):
        payload["capability_versions"] = {
            str(key): str(value)
            for key, value in sorted(capability_versions.items(), key=lambda item: str(item[0]))
            if str(key).strip() and str(value).strip()
        }
    run_artifact = action_response.get("run_artifact")
    if isinstance(run_artifact, dict):
        payload["run_artifact"] = run_artifact
    persistence_backend = action_response.get("persistence_backend")
    if isinstance(persistence_backend, dict):
        payload["persistence_backend"] = persistence_backend
    state_schema_version = action_response.get("state_schema_version")
    if isinstance(state_schema_version, str) and state_schema_version:
        payload["state_schema_version"] = state_schema_version
    migration_status = action_response.get("migration_status")
    if isinstance(migration_status, dict):
        payload["migration_status"] = migration_status
    audit_bundle = action_response.get("audit_bundle")
    if isinstance(audit_bundle, dict):
        payload["audit_bundle"] = audit_bundle
    audit_policy_status = action_response.get("audit_policy_status")
    if isinstance(audit_policy_status, dict):
        payload["audit_policy_status"] = audit_policy_status
    if not ok:
        error_payload = action_response.get("error")
        if isinstance(error_payload, dict):
            payload["error"] = error_payload
        else:
            payload["error"] = {"message": "Action failed"}
    status = 200 if ok else 400
    return _with_headless_contract(payload), status


def merge_response_headers(*header_groups: dict[str, str] | None) -> dict[str, str]:
    merged: dict[str, str] = {}
    for group in header_groups:
        if not isinstance(group, dict):
            continue
        for key, value in group.items():
            if isinstance(key, str) and isinstance(value, str):
                merged[key] = value
    return merged


def _normalize_path(path: str) -> str:
    text = str(path or "")
    normalized = text.rstrip("/")
    return normalized or "/"


def _is_supported_headless_path(path: str) -> bool:
    normalized = _normalize_path(path)
    if normalized == f"{HEADLESS_API_PREFIX}/ui":
        return True
    return normalized.startswith(f"{HEADLESS_API_PREFIX}/actions/")


def _extract_request_token(headers: Mapping[str, object]) -> str | None:
    lowered = {str(key).lower(): value for key, value in headers.items()}
    direct = lowered.get("x-api-token")
    if isinstance(direct, str):
        token = direct.strip()
        if token:
            return token
    authorization = lowered.get("authorization")
    if isinstance(authorization, str):
        text = authorization.strip()
        if text.lower().startswith("bearer "):
            token = text[7:].strip()
            if token:
                return token
    return None


def _authorize_origin(*, headers: Mapping[str, object], cors_origins: object) -> HeadlessRequestGate:
    origin_value = None
    for key, value in headers.items():
        if str(key).lower() == "origin":
            if isinstance(value, str):
                origin_value = value.strip() or None
            break
    if origin_value is None:
        return HeadlessRequestGate(ok=True, headers={})
    allowed_origins = normalize_cors_origins(cors_origins)
    if not allowed_origins:
        return HeadlessRequestGate(
            ok=False,
            status=403,
            payload=_headless_error_payload("Origin is not allowed for this headless endpoint.", kind="authentication"),
        )
    if "*" in allowed_origins:
        return HeadlessRequestGate(ok=True, headers={"Access-Control-Allow-Origin": "*"})
    if origin_value not in allowed_origins:
        return HeadlessRequestGate(
            ok=False,
            status=403,
            payload=_headless_error_payload("Origin is not allowed for this headless endpoint.", kind="authentication"),
        )
    return HeadlessRequestGate(
        ok=True,
        headers={
            "Access-Control-Allow-Origin": origin_value,
            "Vary": "Origin",
        },
    )


def _headless_error_payload(message: str, *, kind: str) -> dict:
    payload = build_error_payload(message, kind=kind)
    return _with_headless_contract(payload)


def _with_headless_contract(payload: dict) -> dict:
    if not isinstance(payload, dict):
        return payload
    payload.setdefault("api_version", HEADLESS_API_VERSION)
    payload.setdefault("contract_version", RUNTIME_UI_CONTRACT_VERSION)
    apply_runtime_spec_versions(payload)
    return payload


def ensure_headless_contract_fields(payload: dict) -> dict:
    return _with_headless_contract(payload)


def _parse_origins_text(value: str) -> tuple[str, ...]:
    parts = [segment.strip() for segment in value.split(",")]
    items = [segment for segment in parts if segment]
    return _dedupe(items)


def _dedupe(values: list[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return tuple(ordered)


def _normalize_etag_token(value: object) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    if text == "*":
        return "*"
    if text.startswith("W/"):
        text = text[2:].strip()
    if not text:
        return None
    return text


__all__ = [
    "HEADLESS_API_PREFIX",
    "HEADLESS_API_VERSION",
    "HeadlessRequestGate",
    "authorize_headless_preflight",
    "authorize_headless_request",
    "build_headless_action_payload",
    "build_headless_ui_payload",
    "build_manifest_hash",
    "ensure_headless_contract_fields",
    "headless_ui_etag",
    "headless_ui_response_headers",
    "headless_action_id",
    "is_headless_ui_path",
    "is_versioned_api_path",
    "merge_response_headers",
    "normalize_api_token",
    "normalize_cors_origins",
    "normalize_headless_action_payload",
    "query_flag",
    "request_etag_matches",
    "unsupported_version_payload",
]
