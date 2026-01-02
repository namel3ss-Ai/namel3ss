from __future__ import annotations

from typing import Mapping


def categorize_ai_error(diagnostic: Mapping[str, object]) -> dict[str, str]:
    status = _coerce_int(diagnostic.get("status"))
    code = _lower(diagnostic.get("code"))
    err_type = _lower(diagnostic.get("type"))
    message = _lower(diagnostic.get("message"))
    network_error = diagnostic.get("network_error")
    network_name = _lower(network_error.get("name")) if isinstance(network_error, Mapping) else ""
    network_message = _lower(network_error.get("message")) if isinstance(network_error, Mapping) else ""

    if _is_missing_key(code, err_type, message):
        return {
            "category": "missing_key",
            "hint": "Set the required API key in .env or export it, then retry.",
            "severity": "error",
        }
    if _is_auth(status, code, err_type, message):
        return {
            "category": "auth",
            "hint": "Check your API key and permissions, then retry.",
            "severity": "error",
        }
    if _is_model_access(code, err_type, message):
        return {
            "category": "model_access",
            "hint": "Use a model you have access to (or update the model name).",
            "severity": "error",
        }
    if _is_rate_limit(status, code, err_type, message):
        return {
            "category": "rate_limit",
            "hint": "You are rate limited. Try again in a moment.",
            "severity": "warn",
        }
    if _is_quota(status, code, message):
        return {
            "category": "quota",
            "hint": "Quota or billing limit reached. Check billing and retry.",
            "severity": "error",
        }
    if _is_timeout(status, code, err_type, message, network_name, network_message):
        return {
            "category": "timeout",
            "hint": "Request timed out. Check your network and retry.",
            "severity": "warn",
        }
    if _is_network(message, network_name, network_message):
        return {
            "category": "network",
            "hint": "Network error reaching the provider. Check connectivity and retry.",
            "severity": "warn",
        }
    if _is_server(status):
        return {
            "category": "server",
            "hint": "Provider server error. Try again shortly.",
            "severity": "warn",
        }
    if _is_malformed_request(status, code, err_type, message):
        return {
            "category": "malformed_request",
            "hint": "Request was rejected. Check model name and inputs.",
            "severity": "error",
        }
    return {
        "category": "unknown",
        "hint": "Check Traces for diagnostics and try again.",
        "severity": "warn",
    }


def _is_missing_key(code: str, err_type: str, message: str) -> bool:
    if "missing" in message and ("api key" in message or "apikey" in message or "api-key" in message):
        return True
    if "set namel3ss_" in message or "set openai_api_key" in message or "set anthropic_api_key" in message:
        return True
    if "missing_api_key" in code or "missing_api_key" in err_type:
        return True
    return False


def _is_auth(status: int | None, code: str, err_type: str, message: str) -> bool:
    if status in {401, 403}:
        return True
    if "invalid_api_key" in code or "invalid_api_key" in err_type:
        return True
    if "unauthorized" in code or "forbidden" in code:
        return True
    if "authentication" in err_type or "auth" in err_type:
        return True
    if "unauthorized" in message or "invalid api key" in message:
        return True
    return False


def _is_model_access(code: str, err_type: str, message: str) -> bool:
    if "model_not_found" in code or "model_not_found" in err_type:
        return True
    if "model_not_supported" in code or "model_not_supported" in err_type:
        return True
    if "model" in message and (
        "not found" in message
        or "does not exist" in message
        or "not available" in message
        or "no access" in message
        or "not have access" in message
    ):
        return True
    return False


def _is_rate_limit(status: int | None, code: str, err_type: str, message: str) -> bool:
    if status == 429:
        return True
    if "rate_limit" in code or "rate_limit" in err_type:
        return True
    if "rate limit" in message:
        return True
    return False


def _is_quota(status: int | None, code: str, message: str) -> bool:
    if status == 402:
        return True
    if "insufficient_quota" in code or "quota" in code:
        return True
    if "quota" in message or "billing" in message:
        return True
    return False


def _is_timeout(
    status: int | None,
    code: str,
    err_type: str,
    message: str,
    network_name: str,
    network_message: str,
) -> bool:
    if "timeout" in err_type or "timeout" in code:
        return True
    if "timeout" in message or "timed out" in message:
        return True
    if "timeout" in network_name or "timeout" in network_message:
        return True
    return False


def _is_network(message: str, network_name: str, network_message: str) -> bool:
    combined = " ".join([message, network_name, network_message]).strip()
    if not combined:
        return False
    for marker in ("unreachable", "network", "connection"):
        if marker in combined:
            return True
    return False


def _is_server(status: int | None) -> bool:
    return status is not None and status >= 500


def _is_malformed_request(status: int | None, code: str, err_type: str, message: str) -> bool:
    if status in {400, 404, 422}:
        return True
    if "invalid_request" in code or "invalid_request" in err_type:
        return True
    if "bad request" in message or "malformed" in message:
        return True
    return False


def _coerce_int(value: object) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def _lower(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


__all__ = ["categorize_ai_error"]
