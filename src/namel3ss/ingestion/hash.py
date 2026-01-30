from __future__ import annotations

import hashlib

from namel3ss.runtime.native import NativeStatus, native_hash


def hash_bytes(data: bytes) -> str:
    outcome = native_hash(data)
    if outcome.status == NativeStatus.OK and outcome.payload is not None:
        try:
            return outcome.payload.decode("utf-8")
        except UnicodeDecodeError:
            pass
    return hashlib.sha256(data).hexdigest()


def hash_text(text: str) -> str:
    return hash_bytes((text or "").encode("utf-8"))


__all__ = ["hash_bytes", "hash_text"]
