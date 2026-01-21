from __future__ import annotations

from typing import Mapping

from namel3ss.config.model import AppConfig
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.errors.payload import build_error_from_exception, build_error_payload
from namel3ss.runtime.auth.auth_context import SESSION_COOKIE_NAME, resolve_auth_context
from namel3ss.runtime.auth.identity_model import build_identity_summary, normalize_identity
from namel3ss.runtime.auth.session_store import SessionStore, redact_session_id
from namel3ss.runtime.auth.studio_adapters import build_session_payload
from namel3ss.runtime.auth.token_codec import issue_token, token_fingerprint
from namel3ss.runtime.auth.trace_events import session_created_event, session_revoked_event
from namel3ss.runtime.identity.context import validate_identity
from namel3ss.schema.identity import IdentitySchema


def handle_session(
    headers: Mapping[str, str] | None,
    *,
    config: AppConfig | None,
    identity_schema: IdentitySchema | None,
    store=None,
) -> tuple[dict, int, dict[str, str]]:
    try:
        context = resolve_auth_context(headers, config=config, identity_schema=identity_schema, store=store)
    except Namel3ssError as err:
        return build_error_from_exception(err, kind="authentication"), 400, {}
    payload = build_session_payload(context)
    if context.error:
        error_payload = _auth_error_payload(context.error)
        error_payload["auth"] = payload.get("auth")
        error_payload["identity"] = payload.get("identity")
        error_payload["session"] = payload.get("session")
        return error_payload, _status_for_auth_error(context.error), {}
    return payload, 200, {}


def handle_login(
    headers: Mapping[str, str] | None,
    body: dict | None,
    *,
    config: AppConfig | None,
    identity_schema: IdentitySchema | None,
    store=None,
) -> tuple[dict, int, dict[str, str]]:
    if not isinstance(body, dict):
        return build_error_payload("Body must be a JSON object.", kind="authentication"), 400, {}
    auth = getattr(config, "authentication", None)
    if auth is None:
        return build_error_payload(_auth_not_configured_message(), kind="authentication"), 400, {}
    identity = None
    if "identity" in body:
        if not auth.allow_identity:
            return build_error_payload(_identity_login_disabled_message(), kind="authentication"), 403, {}
        candidate = body.get("identity")
        if not isinstance(candidate, dict):
            return build_error_payload(_identity_login_body_message(), kind="authentication"), 400, {}
        identity = dict(candidate)
    else:
        identity = _authenticate_credentials(auth, body)
        if identity is None:
            return build_error_payload(_missing_credentials_message(), kind="authentication"), 400, {}
        if identity is False:
            return build_error_payload(_invalid_credentials_message(), kind="authentication"), 401, {}
    normalized = normalize_identity(identity or {})
    if identity_schema is not None:
        try:
            validate_identity(identity_schema, normalized)
        except Namel3ssError as err:
            return build_error_from_exception(err, kind="authentication"), 400, {}
    session_store = SessionStore(_require_store(config, store))
    expires_in = _coerce_positive_int(body.get("expires_in"))
    session = session_store.create_session(normalized, expires_in=expires_in)
    issue_bearer = _coerce_bool(body.get("issue_token"))
    signing_key = getattr(auth, "signing_key", None)
    token_value = None
    token_payload = None
    if issue_bearer:
        if not signing_key:
            return build_error_payload(_missing_signing_key_message(), kind="authentication"), 400, {}
        token_value = issue_token(
            normalized,
            session_id=session.session_id,
            signing_key=signing_key,
            expires_at=session.expires_at,
        )
        token_payload = {
            "status": "issued",
            "token": token_value,
            "fingerprint": token_fingerprint(token_value),
            "expires_at": session.expires_at,
        }
    payload = {
        "ok": True,
        "identity": build_identity_summary(normalized),
        "session": session_store.session_summary(session),
        "traces": [session_created_event(session_id=redact_session_id(session.session_id), subject=normalized.get("subject"))],
    }
    if token_payload:
        payload["token"] = token_payload
    headers_out = {"Set-Cookie": _session_cookie(session.session_id)}
    return payload, 200, headers_out


def handle_logout(
    headers: Mapping[str, str] | None,
    *,
    config: AppConfig | None,
    identity_schema: IdentitySchema | None,
    store=None,
) -> tuple[dict, int, dict[str, str]]:
    context = resolve_auth_context(headers, config=config, identity_schema=identity_schema, store=store)
    if not context.session:
        if context.error:
            return build_error_payload(_auth_error_message(context.error), kind="authentication"), _status_for_auth_error(context.error), {}
        return build_error_payload(_missing_authentication_message(), kind="authentication"), 401, {}
    session_store = SessionStore(_require_store(config, store))
    revoked = session_store.revoke_session(context.session.session_id)
    payload = {
        "ok": True,
        "session": session_store.session_summary(context.session),
        "revoked": bool(revoked),
        "traces": [session_revoked_event(session_id=redact_session_id(context.session.session_id), reason="logout")],
    }
    headers_out = {"Set-Cookie": _session_cookie_clear()}
    return payload, 200, headers_out


def _authenticate_credentials(auth, body: dict) -> dict | None | bool:
    username = body.get("username")
    password = body.get("password")
    if username is None and password is None:
        return None
    if not isinstance(username, str) or not isinstance(password, str):
        return False
    expected_user = getattr(auth, "username", None)
    expected_pass = getattr(auth, "password", None)
    if not expected_user or not expected_pass:
        return False
    if username != expected_user or password != expected_pass:
        return False
    identity = getattr(auth, "identity", None) or {}
    return dict(identity) if isinstance(identity, dict) else {}


def _require_store(config: AppConfig | None, store):
    from namel3ss.runtime.storage.factory import resolve_store

    return resolve_store(store, config=config)


def _session_cookie(session_id: str) -> str:
    return f"{SESSION_COOKIE_NAME}={session_id}; Path=/; HttpOnly; SameSite=Lax"


def _session_cookie_clear() -> str:
    return f"{SESSION_COOKIE_NAME}=; Max-Age=0; Path=/; HttpOnly; SameSite=Lax"


def _coerce_positive_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value > 0:
        return value
    if isinstance(value, str) and value.strip().isdigit():
        parsed = int(value.strip())
        return parsed if parsed > 0 else None
    return None


def _coerce_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return False


def _auth_error_payload(code: str) -> dict:
    return build_error_payload(_auth_error_message(code), kind="authentication", details={"code": code})


def _auth_error_message(code: str) -> str:
    return {
        "missing_authentication": _missing_authentication_message(),
        "token_invalid": _token_invalid_message(),
        "token_expired": _token_expired_message(),
        "session_revoked": _session_revoked_message(),
        "session_expired": _session_expired_message(),
        "session_invalid": _session_revoked_message(),
    }.get(code, _missing_authentication_message())


def _status_for_auth_error(code: str) -> int:
    if code in {"session_revoked", "session_expired"}:
        return 403
    return 401


def _missing_credentials_message() -> str:
    return build_guidance_message(
        what="Login requires credentials.",
        why="No username/password or identity was provided.",
        fix="Provide credentials or enable identity login.",
        example='{"username":"dev","password":"dev"}',
    )


def _invalid_credentials_message() -> str:
    return build_guidance_message(
        what="Credentials are not valid.",
        why="The username or password did not match.",
        fix="Provide the configured credentials.",
        example='{"username":"dev","password":"dev"}',
    )


def _identity_login_disabled_message() -> str:
    return build_guidance_message(
        what="Identity login is disabled.",
        why="Authentication is configured to reject identity-only login.",
        fix="Enable identity login for development or use credentials.",
        example='allow_identity = true',
    )


def _identity_login_body_message() -> str:
    return build_guidance_message(
        what="Identity login requires a JSON object.",
        why="The identity payload must be an object.",
        fix="Provide a JSON object for identity.",
        example='{"identity":{"subject":"dev","role":"admin"}}',
    )


def _auth_not_configured_message() -> str:
    return build_guidance_message(
        what="Authentication is not configured.",
        why="No authentication settings were provided.",
        fix="Set authentication credentials or enable identity login.",
        example='[authentication]\\nusername = "dev"\\npassword = "dev"',
    )


def _missing_signing_key_message() -> str:
    return build_guidance_message(
        what="Token issuance requires a signing key.",
        why="Tokens must be signed to be verified.",
        fix="Set N3_AUTH_SIGNING_KEY or authentication.signing_key.",
        example="N3_AUTH_SIGNING_KEY=dev-key",
    )


def _missing_authentication_message() -> str:
    return build_guidance_message(
        what="Authentication is required.",
        why="No active session or token was provided.",
        fix="Login to create a session or provide a bearer token.",
        example="POST /api/login",
    )


def _token_invalid_message() -> str:
    return build_guidance_message(
        what="Token is not valid.",
        why="The bearer token could not be verified.",
        fix="Provide a valid bearer token.",
        example="Authorization: Bearer <token>",
    )


def _token_expired_message() -> str:
    return build_guidance_message(
        what="Token has expired.",
        why="The bearer token is outside its valid window.",
        fix="Login again to obtain a new token.",
        example="POST /api/login",
    )


def _session_revoked_message() -> str:
    return build_guidance_message(
        what="Session is revoked.",
        why="The session is no longer active.",
        fix="Login again to create a new session.",
        example="POST /api/login",
    )


def _session_expired_message() -> str:
    return build_guidance_message(
        what="Session has expired.",
        why="The session exceeded its valid window.",
        fix="Login again to create a new session.",
        example="POST /api/login",
    )


__all__ = ["handle_login", "handle_logout", "handle_session"]
