from __future__ import annotations

import hashlib
import json
from typing import Any

from namel3ss.errors.base import Namel3ssError

_MAX_SEED = (2**31) - 1


def normalize_seed(value: object | None, *, where: str = "determinism.seed") -> int | str | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise Namel3ssError(f"{where} must be an integer or string.")
    if isinstance(value, int):
        if value < 0:
            raise Namel3ssError(f"{where} must be a non-negative integer.")
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        if text.isdigit():
            parsed = int(text)
            if parsed < 0:
                raise Namel3ssError(f"{where} must be a non-negative integer.")
            return parsed
        return text
    raise Namel3ssError(f"{where} must be an integer or string.")


def resolve_ai_call_seed(
    *,
    explicit_seed: object | None,
    global_seed: object | None,
    model: str,
    user_input: str,
    context: dict[str, object] | None = None,
) -> int:
    explicit = normalize_seed(explicit_seed, where="ask ai seed")
    if isinstance(explicit, int):
        return _bounded(explicit)
    if isinstance(explicit, str):
        return _derive_seed(
            model=model,
            user_input=user_input,
            context=context,
            seed_salt=explicit,
        )
    normalized_global = normalize_seed(global_seed, where="determinism.seed")
    if isinstance(normalized_global, int):
        return _bounded(normalized_global)
    return _derive_seed(
        model=model,
        user_input=user_input,
        context=context,
        seed_salt=normalized_global if isinstance(normalized_global, str) else None,
    )


def seed_from_log_entry(entry: dict[str, object] | None) -> int | None:
    if not isinstance(entry, dict):
        return None
    value = entry.get("seed")
    if isinstance(value, int) and value >= 0:
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def _derive_seed(
    *,
    model: str,
    user_input: str,
    context: dict[str, object] | None,
    seed_salt: str | None,
) -> int:
    payload = {
        "model": str(model or ""),
        "user_input": str(user_input or ""),
        "context": dict(context or {}),
        "seed_salt": seed_salt,
    }
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=_fallback_json,
    ).encode("utf-8")
    digest = hashlib.sha256(encoded).hexdigest()
    return _bounded(int(digest[:8], 16))


def _bounded(value: int) -> int:
    parsed = int(value)
    if parsed <= _MAX_SEED:
        return parsed
    return parsed % _MAX_SEED


def _fallback_json(value: Any) -> str:
    return str(value)


__all__ = ["normalize_seed", "resolve_ai_call_seed", "seed_from_log_entry"]
