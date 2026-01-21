from __future__ import annotations

from namel3ss.traces.schema import TraceEventType


def authorization_identity_event(
    *,
    source: str,
    status: str,
    session_id: str | None = None,
    token: str | None = None,
    subject: str | None = None,
) -> dict:
    event = {
        "type": TraceEventType.IDENTITY_RESOLUTION,
        "source": source,
        "status": status,
    }
    if session_id:
        event["session_id"] = session_id
    if token:
        event["token"] = token
    if subject:
        event["subject"] = subject
    return event


def authorization_check_event(*, subject: str, outcome: str, reason: str | None = None) -> dict:
    event = {
        "type": TraceEventType.AUTHORIZATION_CHECK,
        "subject": subject,
        "outcome": outcome,
    }
    if reason:
        event["reason"] = reason
    return event


def session_created_event(*, session_id: str, subject: str | None = None) -> dict:
    event = {
        "type": TraceEventType.SESSION_CREATED,
        "session_id": session_id,
    }
    if subject:
        event["subject"] = subject
    return event


def session_revoked_event(*, session_id: str, reason: str | None = None) -> dict:
    event = {
        "type": TraceEventType.SESSION_REVOKED,
        "session_id": session_id,
    }
    if reason:
        event["reason"] = reason
    return event


def token_verification_event(*, status: str, token: str | None = None) -> dict:
    event = {
        "type": TraceEventType.TOKEN_VERIFIED,
        "status": status,
    }
    if token:
        event["token"] = token
    return event


__all__ = [
    "authorization_check_event",
    "authorization_identity_event",
    "session_created_event",
    "session_revoked_event",
    "token_verification_event",
]
