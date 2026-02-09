from __future__ import annotations

from collections.abc import Mapping
import re


RUNTIME_ERROR_CATEGORIES: tuple[str, ...] = (
    "server_unavailable",
    "auth_invalid",
    "auth_missing",
    "provider_misconfigured",
    "provider_mock_active",
    "action_denied",
    "policy_denied",
    "upload_failed",
    "ingestion_failed",
    "runtime_internal",
)

_DEFAULTS: dict[str, dict[str, str]] = {
    "server_unavailable": {
        "message": "Runtime server is unavailable.",
        "hint": "Start the runtime server and retry.",
        "origin": "network",
        "stable_code": "runtime.server_unavailable",
    },
    "auth_invalid": {
        "message": "Authentication failed. The token or session is invalid.",
        "hint": "Sign in again or refresh the API token.",
        "origin": "runtime",
        "stable_code": "runtime.auth_invalid",
    },
    "auth_missing": {
        "message": "Authentication is required for this request.",
        "hint": "Sign in or provide a valid API token.",
        "origin": "runtime",
        "stable_code": "runtime.auth_missing",
    },
    "provider_misconfigured": {
        "message": "AI provider is misconfigured.",
        "hint": "Set the selected provider and required API key in configuration.",
        "origin": "provider",
        "stable_code": "runtime.provider_misconfigured",
    },
    "provider_mock_active": {
        "message": "OpenAI key detected but provider is set to mock. Real AI calls are not active.",
        "hint": "Set [answer].provider to a real provider or remove unused keys.",
        "origin": "provider",
        "stable_code": "runtime.provider_mock_active",
    },
    "action_denied": {
        "message": "Action is not allowed in the current context.",
        "hint": "Check action availability, action id, and payload shape.",
        "origin": "runtime",
        "stable_code": "runtime.action_denied",
    },
    "policy_denied": {
        "message": "Policy blocked this action.",
        "hint": "Update policy rules or use an action allowed by policy.",
        "origin": "policy",
        "stable_code": "runtime.policy_denied",
    },
    "upload_failed": {
        "message": "Upload failed.",
        "hint": "Retry the upload and verify file type and size limits.",
        "origin": "runtime",
        "stable_code": "runtime.upload_failed",
    },
    "ingestion_failed": {
        "message": "Ingestion failed.",
        "hint": "Review ingestion diagnostics and retry ingestion.",
        "origin": "runtime",
        "stable_code": "runtime.ingestion_failed",
    },
    "runtime_internal": {
        "message": "Runtime internal error.",
        "hint": "Retry the request. If the problem persists, inspect logs and traces.",
        "origin": "runtime",
        "stable_code": "runtime.runtime_internal",
    },
}

_SECRET_REPLACEMENTS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"Bearer\s+[A-Za-z0-9._-]+", flags=re.IGNORECASE), "Bearer [redacted]"),
    (re.compile(r"sk-[A-Za-z0-9_-]+"), "[redacted]"),
)

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def build_runtime_error(
    category: str,
    *,
    message: str | None = None,
    hint: str | None = None,
    origin: str | None = None,
    stable_code: str | None = None,
) -> dict[str, str]:
    normalized_category = _normalize_category(category)
    defaults = _DEFAULTS[normalized_category]
    payload = {
        "category": normalized_category,
        "message": _safe_text(message) or defaults["message"],
        "hint": _safe_text(hint) or defaults["hint"],
        "origin": _safe_text(origin) or defaults["origin"],
        "stable_code": _safe_text(stable_code) or defaults["stable_code"],
    }
    return payload


def classify_runtime_error(
    *,
    message: str | None,
    kind: str | None,
    details: Mapping[str, object] | None = None,
    status_code: int | None = None,
    endpoint: str | None = None,
    payload: Mapping[str, object] | None = None,
) -> dict[str, str]:
    details_map = details if isinstance(details, Mapping) else {}
    payload_map = payload if isinstance(payload, Mapping) else {}
    resolved_message = _safe_text(message) or _fallback_message(payload_map)
    category = _resolve_category(
        message=resolved_message,
        kind=kind,
        details=details_map,
        status_code=status_code,
        endpoint=endpoint,
        payload=payload_map,
    )
    stable_code = _stable_code(category, details=details_map, kind=kind)
    return build_runtime_error(
        category,
        message=resolved_message or None,
        stable_code=stable_code,
    )


def is_runtime_error_category(value: object) -> bool:
    return isinstance(value, str) and value in RUNTIME_ERROR_CATEGORIES


def _resolve_category(
    *,
    message: str,
    kind: str | None,
    details: Mapping[str, object],
    status_code: int | None,
    endpoint: str | None,
    payload: Mapping[str, object],
) -> str:
    kind_text = (kind or "").strip().lower()
    msg = message.lower()
    endpoint_text = (endpoint or "").strip().lower()
    details_category = str(details.get("category") or "").strip().lower()
    reason_code = str(details.get("reason_code") or "").strip().lower()

    if _looks_like_server_unavailable(msg, status_code=status_code):
        return "server_unavailable"
    if "upload" in endpoint_text:
        return "upload_failed"
    if "ingestion" in endpoint_text:
        return "ingestion_failed"
    if payload.get("upload") and bool(payload.get("ok")) is False:
        return "upload_failed"
    if "ingestion" in msg or str(details.get("action") or "").startswith("ingestion"):
        return "ingestion_failed"
    if kind_text in {"authentication", "auth"} or details_category == "authentication":
        return "auth_missing" if _looks_like_auth_missing(msg) else "auth_invalid"
    if status_code in {401, 403}:
        return "auth_missing" if _looks_like_auth_missing(msg) else "auth_invalid"
    if _is_provider_mock_active(message=msg, reason_code=reason_code):
        return "provider_mock_active"
    if _is_provider_misconfigured(
        message=msg,
        kind_text=kind_text,
        details_category=details_category,
        reason_code=reason_code,
    ):
        return "provider_misconfigured"
    if _is_policy_denied(kind_text=kind_text, details_category=details_category, reason_code=reason_code, message=msg):
        return "policy_denied"
    if _is_action_denied(
        kind_text=kind_text,
        details_category=details_category,
        reason_code=reason_code,
        message=msg,
    ):
        return "action_denied"
    return "runtime_internal"


def _stable_code(category: str, *, details: Mapping[str, object], kind: str | None) -> str:
    base = _DEFAULTS[category]["stable_code"]
    reason = str(details.get("reason_code") or details.get("error_id") or "").strip().lower()
    if reason:
        token = _slug_token(reason)
        if token:
            return f"{base}.{token}"
    if category == "provider_misconfigured":
        provider = str(details.get("provider") or "").strip().lower()
        token = _slug_token(provider)
        if token:
            return f"{base}.{token}"
    if category == "runtime_internal":
        token = _slug_token(str(kind or ""))
        if token:
            return f"{base}.{token}"
    return base


def _slug_token(value: str) -> str:
    token = _SLUG_RE.sub("_", value.strip().lower()).strip("_")
    return token


def _looks_like_auth_missing(message: str) -> bool:
    return any(token in message for token in ("missing token", "token is required", "auth required", "sign in"))


def _looks_like_server_unavailable(message: str, *, status_code: int | None) -> bool:
    if status_code in {502, 503, 504}:
        return True
    tokens = (
        "failed to fetch",
        "networkerror",
        "connection refused",
        "connection reset",
        "server unavailable",
        "disconnected",
        "gateway timeout",
    )
    return any(token in message for token in tokens)


def _is_provider_misconfigured(
    *,
    message: str,
    kind_text: str,
    details_category: str,
    reason_code: str,
) -> bool:
    if details_category == "provider" or kind_text in {"provider", "ai_provider"}:
        return True
    if "provider" in reason_code and "mock_active" not in reason_code:
        return True
    tokens = (
        "provider is misconfigured",
        "missing namel3ss_",
        "missing openai_api_key",
        "missing api key",
        "unknown ai provider",
        "provider configuration",
    )
    return any(token in message for token in tokens)


def _is_provider_mock_active(*, message: str, reason_code: str) -> bool:
    if "provider_mock_active" in reason_code:
        return True
    if "provider is set to mock" in message and "key detected" in message:
        return True
    if "real ai calls are not active" in message:
        return True
    return False


def _is_policy_denied(*, kind_text: str, details_category: str, reason_code: str, message: str) -> bool:
    if details_category == "policy":
        return True
    if reason_code in {"policy_denied", "ingestion_policy_denied"}:
        return True
    if "blocked by policy" in message:
        return True
    return kind_text == "policy"


def _is_action_denied(*, kind_text: str, details_category: str, reason_code: str, message: str) -> bool:
    if reason_code in {"action_denied", "action_disabled", "unknown_action"}:
        return True
    if "action id is required" in message:
        return True
    if "unknown action" in message:
        return True
    if "action is disabled" in message:
        return True
    if details_category in {"permission", "authorization"}:
        return True
    return kind_text in {"permission"}


def _fallback_message(payload: Mapping[str, object]) -> str:
    error = payload.get("error")
    if isinstance(error, Mapping):
        for key in ("message", "error", "why"):
            value = error.get(key)
            text = _safe_text(value)
            if text:
                return text
    text = _safe_text(error)
    if text:
        return text
    return _safe_text(payload.get("message"))


def _normalize_category(category: str) -> str:
    text = str(category or "").strip()
    if text in _DEFAULTS:
        return text
    return "runtime_internal"


def _safe_text(value: object) -> str:
    if not isinstance(value, str):
        return ""
    text = " ".join(value.split()).strip()
    if not text:
        return ""
    for pattern, replacement in _SECRET_REPLACEMENTS:
        text = pattern.sub(replacement, text)
    return text[:280]


__all__ = [
    "RUNTIME_ERROR_CATEGORIES",
    "build_runtime_error",
    "classify_runtime_error",
    "is_runtime_error_category",
]
