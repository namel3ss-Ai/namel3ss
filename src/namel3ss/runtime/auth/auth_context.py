from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Mapping

from namel3ss.config.model import AppConfig
from namel3ss.runtime.auth.identity_model import normalize_identity
from namel3ss.runtime.auth.session_store import SessionRecord, SessionStore, redact_session_id
from namel3ss.runtime.auth.token_codec import TokenVerification, token_fingerprint, verify_token
from namel3ss.runtime.identity.context import resolve_identity, validate_identity
from namel3ss.schema.identity import IdentitySchema
from namel3ss.runtime.storage.factory import resolve_store
from namel3ss.governance.rbac import resolve_identity_from_token
from namel3ss.runtime.auth.trace_events import (
    authorization_identity_event,
    token_verification_event,
)


SESSION_COOKIE_NAME = "n3_session"


@dataclass(frozen=True)
class AuthContext:
    identity: dict
    source: str
    authenticated: bool
    error: str | None
    session: SessionRecord | None
    session_summary: dict | None
    token_status: str | None
    token_fingerprint: str | None
    traces: list[dict]


def resolve_auth_context(
    headers: Mapping[str, str] | None,
    *,
    config: AppConfig | None,
    identity_schema: IdentitySchema | None,
    store=None,
    project_root: str | None = None,
    app_path: str | None = None,
) -> AuthContext:
    resolved_config = config
    resolved_store = resolve_store(store, config=resolved_config)
    session_store = SessionStore(resolved_store)
    traces: list[dict] = []
    session_id = _session_id_from_headers(headers)
    if session_id:
        now_tick = session_store.tick()
        session = session_store.get_session(session_id, now_tick=now_tick)
        if session is None:
            traces.append(authorization_identity_event(source="session", status="missing", session_id=redact_session_id(session_id)))
            return AuthContext(
                identity={},
                source="session",
                authenticated=False,
                error="session_revoked",
                session=None,
                session_summary=None,
                token_status=None,
                token_fingerprint=None,
                traces=traces,
            )
        traces.append(
            authorization_identity_event(
                source="session",
                status=session.status,
                session_id=redact_session_id(session.session_id),
            )
        )
        if session.status == "revoked":
            return AuthContext(
                identity={},
                source="session",
                authenticated=False,
                error="session_revoked",
                session=session,
                session_summary=session_store.session_summary(session),
                token_status=None,
                token_fingerprint=None,
                traces=traces,
            )
        if session.status == "expired":
            return AuthContext(
                identity={},
                source="session",
                authenticated=False,
                error="session_expired",
                session=session,
                session_summary=session_store.session_summary(session),
                token_status=None,
                token_fingerprint=None,
                traces=traces,
            )
        identity = normalize_identity(session.identity)
        _validate_identity(identity_schema, identity)
        return AuthContext(
            identity=identity,
            source="session",
            authenticated=True,
            error=None,
            session=session,
            session_summary=session_store.session_summary(session),
            token_status=None,
            token_fingerprint=None,
            traces=traces,
        )
    token = _bearer_token_from_headers(headers)
    if token:
        token_id = token_fingerprint(token)
        signing_key = getattr(getattr(resolved_config, "authentication", None), "signing_key", None)
        if not signing_key:
            static_identity = resolve_identity_from_token(
                token,
                project_root=project_root,
                app_path=app_path,
            )
            if isinstance(static_identity, dict):
                traces.append(token_verification_event(status="static", token=token_id))
                _validate_identity(identity_schema, static_identity)
                return AuthContext(
                    identity=normalize_identity(static_identity),
                    source="token",
                    authenticated=True,
                    error=None,
                    session=None,
                    session_summary=None,
                    token_status="static",
                    token_fingerprint=token_id,
                    traces=traces,
                )
            token_status = "revoked"
            traces.append(token_verification_event(status=token_status, token=token_id))
            return AuthContext(
                identity={},
                source="token",
                authenticated=False,
                error="token_invalid",
                session=None,
                session_summary=None,
                token_status=token_status,
                token_fingerprint=token_id,
                traces=traces,
            )
        verification = verify_token(token, signing_key=signing_key)
        if verification.status != "valid" or not verification.payload:
            static_identity = resolve_identity_from_token(
                token,
                project_root=project_root,
                app_path=app_path,
            )
            if isinstance(static_identity, dict):
                traces.append(token_verification_event(status="static", token=token_id))
                _validate_identity(identity_schema, static_identity)
                return AuthContext(
                    identity=normalize_identity(static_identity),
                    source="token",
                    authenticated=True,
                    error=None,
                    session=None,
                    session_summary=None,
                    token_status="static",
                    token_fingerprint=token_id,
                    traces=traces,
                )
            token_status = "revoked"
            traces.append(token_verification_event(status=token_status, token=token_id))
            return AuthContext(
                identity={},
                source="token",
                authenticated=False,
                error="token_invalid",
                session=None,
                session_summary=None,
                token_status=token_status,
                token_fingerprint=token_id,
                traces=traces,
            )
        now_tick = session_store.tick()
        expires_at = _coerce_int(verification.payload.get("expires_at"))
        if expires_at is not None and now_tick >= expires_at:
            token_status = "expired"
            traces.append(token_verification_event(status=token_status, token=token_id))
            return AuthContext(
                identity={},
                source="token",
                authenticated=False,
                error="token_expired",
                session=None,
                session_summary=None,
                token_status=token_status,
                token_fingerprint=token_id,
                traces=traces,
            )
        session = None
        session_id = verification.payload.get("session_id")
        if isinstance(session_id, str) and session_id:
            session = session_store.get_session(session_id, now_tick=now_tick)
            if session is None:
                token_status = "revoked"
                traces.append(token_verification_event(status=token_status, token=token_id))
                return AuthContext(
                    identity={},
                    source="token",
                    authenticated=False,
                    error="token_invalid",
                    session=None,
                    session_summary=None,
                    token_status=token_status,
                    token_fingerprint=token_id,
                    traces=traces,
                )
            if session.status == "revoked":
                token_status = "revoked"
                traces.append(token_verification_event(status=token_status, token=token_id))
                return AuthContext(
                    identity={},
                    source="token",
                    authenticated=False,
                    error="session_revoked",
                    session=session,
                    session_summary=session_store.session_summary(session),
                    token_status=token_status,
                    token_fingerprint=token_id,
                    traces=traces,
                )
            if session.status == "expired":
                token_status = "expired"
                traces.append(token_verification_event(status=token_status, token=token_id))
                return AuthContext(
                    identity={},
                    source="token",
                    authenticated=False,
                    error="session_expired",
                    session=session,
                    session_summary=session_store.session_summary(session),
                    token_status=token_status,
                    token_fingerprint=token_id,
                    traces=traces,
                )
        identity = normalize_identity(verification.payload)
        _validate_identity(identity_schema, identity)
        token_status = "valid"
        traces.append(token_verification_event(status=token_status, token=token_id))
        return AuthContext(
            identity=identity,
            source="token",
            authenticated=True,
            error=None,
            session=session,
            session_summary=session_store.session_summary(session),
            token_status=token_status,
            token_fingerprint=token_id,
            traces=traces,
        )
    identity = resolve_identity(resolved_config, identity_schema)
    identity = normalize_identity(identity)
    _validate_identity(identity_schema, identity)
    source = "config" if identity else "none"
    authenticated = bool(identity)
    traces.append(authorization_identity_event(source=source, status="resolved"))
    return AuthContext(
        identity=identity,
        source=source,
        authenticated=authenticated,
        error="missing_authentication" if not authenticated else None,
        session=None,
        session_summary=None,
        token_status=None,
        token_fingerprint=None,
        traces=traces,
    )


def _session_id_from_headers(headers: Mapping[str, str] | None) -> str | None:
    cookies = _parse_cookie_header(_header_value(headers, "cookie"))
    value = cookies.get(SESSION_COOKIE_NAME)
    if value:
        return value
    return None


def _bearer_token_from_headers(headers: Mapping[str, str] | None) -> str | None:
    value = _header_value(headers, "authorization")
    if not value:
        return None
    parts = value.strip().split(" ", 1)
    if len(parts) != 2:
        return None
    scheme, token = parts
    if scheme.lower() != "bearer":
        return None
    token = token.strip()
    return token or None


def _header_value(headers: Mapping[str, str] | None, key: str) -> str | None:
    if not headers:
        return None
    for name, value in headers.items():
        if name.lower() == key:
            return value
    return None


def _parse_cookie_header(raw: str | None) -> dict[str, str]:
    cookies: dict[str, str] = {}
    if not raw:
        return cookies
    for part in raw.split(";"):
        if "=" not in part:
            continue
        name, value = part.split("=", 1)
        name = name.strip()
        value = value.strip()
        if not name:
            continue
        cookies[name] = value
    return cookies


def _validate_identity(schema: IdentitySchema | None, identity: dict) -> None:
    if schema is None:
        return
    validate_identity(schema, identity)


def _coerce_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, Decimal):
        return int(value)
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


__all__ = ["AuthContext", "SESSION_COOKIE_NAME", "resolve_auth_context"]
