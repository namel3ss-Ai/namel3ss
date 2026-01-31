from __future__ import annotations

from namel3ss.lexer.scan_payload import payload_to_tokens
from namel3ss.runtime.native import NativeStatus, native_scan


def scan_tokens_native(source: str):
    outcome = native_scan(source.encode("utf-8"))
    if outcome.status != NativeStatus.OK or outcome.payload is None:
        return None
    try:
        return payload_to_tokens(outcome.payload)
    except Exception:
        return None


__all__ = ["scan_tokens_native"]
