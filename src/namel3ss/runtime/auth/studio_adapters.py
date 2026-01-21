from __future__ import annotations

from namel3ss.runtime.auth.auth_context import AuthContext
from namel3ss.runtime.auth.identity_model import build_identity_summary


def build_session_payload(context: AuthContext) -> dict:
    payload = {
        "ok": True,
        "auth": {
            "authenticated": context.authenticated,
            "source": context.source,
            "error": context.error,
            "token_status": context.token_status,
            "token": context.token_fingerprint,
        },
        "identity": build_identity_summary(context.identity),
        "session": context.session_summary,
    }
    return payload


__all__ = ["build_session_payload"]
