from __future__ import annotations

import json
from hashlib import sha256

from namel3ss.runtime.memory.events import normalize_text


def fingerprint_query(text: str) -> str:
    normalized = normalize_text(text or "")
    return _hash_text(normalized)


def fingerprint_policy(snapshot: dict) -> str:
    payload = json.dumps(snapshot or {}, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return _hash_text(payload)


def build_cache_key(
    *,
    space: str,
    lane: str,
    phase_id: str,
    ai_profile: str,
    query_fingerprint: str,
    policy_fingerprint: str,
    store_key: str | None = None,
) -> str:
    raw = "|".join(
        [
            str(space or ""),
            str(lane or ""),
            str(phase_id or ""),
            str(ai_profile or ""),
            str(store_key or ""),
            str(query_fingerprint or ""),
            str(policy_fingerprint or ""),
        ]
    )
    return _hash_text(raw)


def _hash_text(value: str) -> str:
    payload = value.encode("utf-8")
    return sha256(payload).hexdigest()


__all__ = ["build_cache_key", "fingerprint_policy", "fingerprint_query"]
