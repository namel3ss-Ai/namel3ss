from __future__ import annotations

import base64
import hashlib
import hmac
import json
from dataclasses import dataclass

from namel3ss.runtime.auth.identity_model import normalize_identity


TOKEN_PREFIX = "n3"


@dataclass(frozen=True)
class TokenVerification:
    status: str
    payload: dict | None = None


def issue_token(
    identity: dict | None,
    *,
    session_id: str | None,
    signing_key: str,
    expires_at: int | None = None,
) -> str:
    payload = _build_payload(identity, session_id=session_id, expires_at=expires_at)
    encoded = _encode_payload(payload)
    signature = _sign(encoded, signing_key)
    return f"{TOKEN_PREFIX}.{encoded}.{signature}"


def verify_token(token: str, *, signing_key: str) -> TokenVerification:
    if not isinstance(token, str) or not token:
        return TokenVerification(status="invalid", payload=None)
    parts = token.split(".")
    if len(parts) != 3 or parts[0] != TOKEN_PREFIX:
        return TokenVerification(status="invalid", payload=None)
    encoded = parts[1]
    signature = parts[2]
    expected = _sign(encoded, signing_key)
    if not hmac.compare_digest(signature, expected):
        return TokenVerification(status="invalid", payload=None)
    payload = _decode_payload(encoded)
    if payload is None:
        return TokenVerification(status="invalid", payload=None)
    return TokenVerification(status="valid", payload=payload)


def token_fingerprint(token: str) -> str:
    if not isinstance(token, str) or not token:
        return "token:missing"
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    return f"token:{digest[:12]}"


def _build_payload(identity: dict | None, *, session_id: str | None, expires_at: int | None) -> dict:
    normalized = normalize_identity(identity)
    payload = {
        "subject": normalized.get("subject"),
        "roles": list(normalized.get("roles") or []),
        "permissions": list(normalized.get("permissions") or []),
        "trust_level": normalized.get("trust_level"),
    }
    if session_id:
        payload["session_id"] = session_id
    if expires_at is not None:
        payload["expires_at"] = int(expires_at)
    return payload


def _encode_payload(payload: dict) -> str:
    data = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return _b64url_encode(data.encode("utf-8"))


def _decode_payload(encoded: str) -> dict | None:
    try:
        raw = _b64url_decode(encoded)
    except Exception:
        return None
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except Exception:
        return None
    if not isinstance(parsed, dict):
        return None
    return parsed


def _sign(encoded: str, signing_key: str) -> str:
    digest = hmac.new(signing_key.encode("utf-8"), encoded.encode("utf-8"), hashlib.sha256).digest()
    return _b64url_encode(digest)


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64url_decode(text: str) -> bytes:
    pad = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode((text + pad).encode("ascii"))


__all__ = ["TOKEN_PREFIX", "TokenVerification", "issue_token", "token_fingerprint", "verify_token"]
