from __future__ import annotations

import json
import re
from typing import Iterable
from urllib.error import HTTPError, URLError

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.ai.providers._shared.diagnostics import categorize_ai_error
from namel3ss.secrets import collect_secret_values, record_secret_access, redact_payload, redact_text


def require_env(provider_name: str, env_var: str, value: str | None) -> str:
    if value is None or str(value).strip() == "":
        short_var = env_var.replace("NAMEL3SS_", "")
        raise Namel3ssError(
            f"Missing {short_var}. Fix: set {env_var} in .env or export it, then re-run."
        )
    record_secret_access(env_var, caller=f"provider:{provider_name}", source="env")
    return value


def map_http_error(
    provider_name: str,
    err: HTTPError | URLError | TimeoutError | Exception,
    *,
    url: str | None = None,
    body: bytes | None = None,
    secret_values: Iterable[str] | None = None,
) -> Namel3ssError:
    details: dict[str, object] = {"provider": provider_name}
    if url:
        details["url"] = url
    status = None
    code = None
    err_type = None
    message = None
    network_error = None
    if isinstance(err, HTTPError):
        status = err.code
        details["status"] = err.code
        if provider_name == "openai":
            error_info = _extract_openai_error(body, secret_values)
            if error_info:
                details["error"] = error_info
                code = error_info.get("code")
                err_type = error_info.get("type")
                message = error_info.get("message")
    if not isinstance(err, HTTPError) and isinstance(err, (URLError, TimeoutError, OSError)):
        network_error = _summarize_network_exception(_select_network_exception(err), secret_values)
        message = _format_network_message(network_error) or message or "unreachable"
        details["network_error"] = network_error
    details["diagnostic"] = build_provider_diagnostic(
        provider_name,
        url=url,
        status=status,
        code=code,
        error_type=err_type,
        message=message,
        network_error=network_error,
        secret_values=secret_values,
    )
    if isinstance(err, HTTPError) and err.code in {401, 403}:
        return Namel3ssError(f"Provider '{provider_name}' authentication failed", details=details)
    if not isinstance(err, HTTPError) and isinstance(err, (URLError, TimeoutError, OSError)):
        return Namel3ssError(f"Provider '{provider_name}' unreachable", details=details)
    return Namel3ssError(f"Provider '{provider_name}' returned an invalid response", details=details)


def build_provider_diagnostic(
    provider_name: str,
    *,
    url: str | None = None,
    status: int | None = None,
    code: str | None = None,
    error_type: str | None = None,
    message: str | None = None,
    network_error: dict[str, object] | None = None,
    secret_values: Iterable[str] | None = None,
) -> dict[str, object]:
    message_value = _coerce_str(message)
    if message_value:
        message_value = _truncate(_compact_text(_redact_text(message_value, secret_values)))
    diagnostic = {
        "provider": provider_name,
        "url": url,
        "status": status,
        "code": _coerce_str(code),
        "type": _coerce_str(error_type),
        "message": message_value,
        "network_error": network_error,
    }
    diagnostic.update(categorize_ai_error(diagnostic))
    return diagnostic


def _select_network_exception(err: Exception) -> Exception:
    if isinstance(err, URLError):
        reason = getattr(err, "reason", None)
        if isinstance(reason, Exception):
            return reason
    cause = err.__cause__ or err.__context__
    if isinstance(cause, Exception):
        return cause
    return err


def _summarize_network_exception(
    err: Exception,
    secret_values: Iterable[str] | None,
    *,
    depth: int = 0,
) -> dict[str, object]:
    summary: dict[str, object] = {"name": err.__class__.__name__}
    message = _coerce_str(_extract_exception_message(err).strip())
    if message:
        message = _truncate(_compact_text(_sanitize_message(message, secret_values)), limit=200)
        summary["message"] = message
    errno = getattr(err, "errno", None)
    if isinstance(errno, int):
        summary["errno"] = errno
    if depth < 1:
        cause = err.__cause__ or err.__context__
        if isinstance(cause, Exception):
            summary["cause"] = _summarize_network_exception(cause, secret_values, depth=depth + 1)
    return summary


def _format_network_message(network_error: dict[str, object] | None) -> str | None:
    if not network_error:
        return None
    name = _coerce_str(network_error.get("name"))
    message = _coerce_str(network_error.get("message"))
    if message and name:
        return f"unreachable: {name}: {message}"
    if message:
        return f"unreachable: {message}"
    if name:
        return f"unreachable: {name}"
    return "unreachable"


def _sanitize_message(message: str, secret_values: Iterable[str] | None) -> str:
    redacted = _redact_text(message, secret_values)
    redacted = re.sub(r"Bearer\\s+\\S+", "[redacted]", redacted)
    redacted = redacted.replace("Bearer", "[redacted]")
    redacted = re.sub(r"sk-[A-Za-z0-9_-]+", "[redacted]", redacted)
    return redacted


def _extract_exception_message(err: Exception) -> str:
    args = getattr(err, "args", ())
    if len(args) == 1 and isinstance(args[0], str):
        return args[0]
    return str(err)


def _extract_openai_error(body: bytes | None, secret_values: Iterable[str] | None) -> dict[str, str] | None:
    if not body:
        return None
    text = None
    try:
        text = body.decode("utf-8")
        payload = json.loads(text)
    except Exception:
        message = _compact_text(text or "")
        if not message:
            return None
        return {"message": _truncate(_redact_text(message, secret_values))}
    if not isinstance(payload, dict):
        return None
    error = payload.get("error")
    if not isinstance(error, dict):
        return None
    redacted = _redact_payload(error, secret_values)
    code = _coerce_str(redacted.get("code"))
    err_type = _coerce_str(redacted.get("type"))
    message = _coerce_str(redacted.get("message"))
    if message:
        message = _truncate(_compact_text(message))
    result: dict[str, str] = {}
    if code:
        result["code"] = code
    if err_type:
        result["type"] = err_type
    if message:
        result["message"] = message
    return result or None


def _redact_payload(payload: dict, secret_values: Iterable[str] | None) -> dict:
    return redact_payload(payload, _merged_secret_values(secret_values))


def _redact_text(value: str, secret_values: Iterable[str] | None) -> str:
    return redact_text(value, _merged_secret_values(secret_values))


def _merged_secret_values(secret_values: Iterable[str] | None) -> list[str]:
    merged = list(secret_values or [])
    merged.extend(collect_secret_values())
    return merged


def _coerce_str(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return str(value)


def _compact_text(text: str) -> str:
    return " ".join(text.split())


def _truncate(text: str, limit: int = 240) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."
