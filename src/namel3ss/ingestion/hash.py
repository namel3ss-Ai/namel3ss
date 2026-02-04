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


def hash_chunk(*, document_id: str, page_number: int, chunk_index: int, text: str) -> str:
    payload = "\n".join(
        [
            str(document_id or ""),
            str(int(page_number)),
            str(int(chunk_index)),
            text or "",
        ]
    )
    return hash_text(payload)


__all__ = ["hash_bytes", "hash_chunk", "hash_text"]
