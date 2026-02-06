from __future__ import annotations

import hashlib
import json

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.ai.provider import AIResponse
from namel3ss.runtime.ai.providers._shared.parse import normalize_ai_text


def parse_payload(user_input: str) -> dict[str, object] | None:
    if not isinstance(user_input, str):
        return None
    text = user_input.strip()
    if not text.startswith("{"):
        return None
    try:
        value = json.loads(text)
    except Exception:
        return None
    if not isinstance(value, dict):
        return None
    return value


def input_mode(user_input: str) -> str:
    payload = parse_payload(user_input)
    if not payload:
        return "text"
    mode = str(payload.get("mode") or "text").strip().lower()
    return mode or "text"


def payload_seed(user_input: str) -> int | None:
    payload = parse_payload(user_input)
    if not payload:
        return None
    value = payload.get("seed")
    if isinstance(value, int) and value >= 0:
        return value
    return None


def digest_for_call(*, provider: str, model: str, system_prompt: str | None, user_input: str, seed: int | None = None) -> str:
    canonical = {
        "provider": provider,
        "model": model,
        "system_prompt": system_prompt or "",
        "user_input": user_input,
        "seed": seed,
    }
    encoded = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def deterministic_label(digest: str, labels: tuple[str, ...]) -> str:
    if not labels:
        return "unknown"
    index = int(digest[:8], 16) % len(labels)
    return labels[index]


def ensure_mode_supported(*, provider: str, mode: str, allowed: tuple[str, ...]) -> None:
    token = str(mode or "text").strip().lower()
    if token == "structured":
        token = "text"
    if token in allowed:
        return
    choices = ", ".join(allowed)
    raise Namel3ssError(
        f"Provider '{provider}' does not support mode '{token}'. Supported modes: {choices}."
    )


def text_response(text: str, *, provider_name: str) -> AIResponse:
    normalized = normalize_ai_text(text, provider_name=provider_name)
    return AIResponse(output=normalized)


__all__ = [
    "deterministic_label",
    "digest_for_call",
    "ensure_mode_supported",
    "input_mode",
    "parse_payload",
    "payload_seed",
    "text_response",
]
