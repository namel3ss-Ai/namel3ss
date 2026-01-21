from __future__ import annotations

from base64 import b64encode

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.secrets_store import SecretValue


def auth_bearer(secret: SecretValue) -> dict[str, SecretValue]:
    _require_secret_value(secret, context="Bearer token")
    redacted = _redacted_label("Bearer", secret.secret_names)
    actual = f"Bearer {secret.secret_value}"
    return {"Authorization": SecretValue(redacted, secret_names=secret.secret_names, secret_value=actual)}


def auth_basic(user: SecretValue, password: SecretValue) -> dict[str, SecretValue]:
    _require_secret_value(user, context="Basic username")
    _require_secret_value(password, context="Basic password")
    token = f"{user.secret_value}:{password.secret_value}"
    encoded = b64encode(token.encode("utf-8")).decode("ascii")
    combined = _merge_secret_names(user.secret_names, password.secret_names)
    redacted = _redacted_label("Basic", combined)
    actual = f"Basic {encoded}"
    return {"Authorization": SecretValue(redacted, secret_names=combined, secret_value=actual)}


def auth_header(header_name: str, secret: SecretValue) -> dict[str, SecretValue]:
    _require_secret_value(secret, context="header value")
    header = (header_name or "").strip()
    if not header:
        raise Namel3ssError(
            build_guidance_message(
                what="Header name is missing.",
                why="Auth headers require a header name.",
                fix="Provide a header name.",
                example='auth_header("X-API-Key", secret("stripe_key"))',
            )
        )
    redacted = _redacted_label(header, secret.secret_names)
    return {header: SecretValue(redacted, secret_names=secret.secret_names, secret_value=secret.secret_value)}


def _require_secret_value(value: object, *, context: str) -> None:
    if isinstance(value, SecretValue):
        return
    raise Namel3ssError(
        build_guidance_message(
            what=f"{context} must come from secret().",
            why="Secrets must not be hard-coded.",
            fix="Use secret(\"name\") to load the value.",
            example='auth_bearer(secret("stripe_key"))',
        )
    )


def _redacted_label(prefix: str, names: tuple[str, ...]) -> str:
    label = ",".join(names) if names else "secret"
    return f"{prefix} [redacted: {label}]"


def _merge_secret_names(left: tuple[str, ...], right: tuple[str, ...]) -> tuple[str, ...]:
    seen: list[str] = []
    for name in (*left, *right):
        if name and name not in seen:
            seen.append(name)
    return tuple(seen)


__all__ = ["auth_basic", "auth_bearer", "auth_header"]
