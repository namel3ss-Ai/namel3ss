from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass


DEFAULT_ALGORITHM = "hmac-sha256"
LEGACY_ALGORITHM = "sha256"


@dataclass(frozen=True)
class SignaturePayload:
    algorithm: str
    signature: str


def parse_signature_text(text: str) -> SignaturePayload | None:
    value = text.strip()
    if not value:
        return None
    if ":" in value:
        algorithm, signature = value.split(":", 1)
        algorithm = algorithm.strip()
        signature = signature.strip()
        if algorithm and signature:
            return SignaturePayload(algorithm=algorithm, signature=signature)
    return SignaturePayload(algorithm=DEFAULT_ALGORITHM, signature=value)


def normalize_key_text(text: str) -> str:
    value = text.strip()
    prefix = f"{DEFAULT_ALGORITHM}:"
    if value.startswith(prefix):
        return value[len(prefix) :].strip()
    return value


def sign_digest(digest: str, key_text: str) -> str:
    key = normalize_key_text(key_text).encode("utf-8")
    signature = hmac.new(key, digest.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{DEFAULT_ALGORITHM}:{signature}"


def verify_signature(digest: str, signature_text: str, key_text: str) -> bool:
    payload = parse_signature_text(signature_text)
    if payload is None:
        return False
    if payload.algorithm == DEFAULT_ALGORITHM:
        expected = sign_digest(digest, key_text)
        expected_payload = parse_signature_text(expected)
        if expected_payload is None:
            return False
        return hmac.compare_digest(payload.signature, expected_payload.signature)
    if payload.algorithm == LEGACY_ALGORITHM:
        normalized = payload.signature
        if normalized.startswith("sha256:"):
            normalized = normalized.split(":", 1)[1]
        digest_value = digest
        if digest_value.startswith("sha256:"):
            digest_value = digest_value.split(":", 1)[1]
        key_value = normalize_key_text(key_text)
        return normalized == digest_value and (key_value == normalized or key_value == digest)
    return False


__all__ = [
    "DEFAULT_ALGORITHM",
    "LEGACY_ALGORITHM",
    "SignaturePayload",
    "parse_signature_text",
    "normalize_key_text",
    "sign_digest",
    "verify_signature",
]
