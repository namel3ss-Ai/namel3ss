from __future__ import annotations

from namel3ss.runtime.ai.providers.registry import get_provider
from namel3ss.runtime.executor.context import ExecutionContext
from namel3ss.runtime.providers.capabilities import get_provider_capabilities


def _resolve_provider(ctx: ExecutionContext, provider_name: str):
    key = provider_name.lower()
    _ = get_provider_capabilities(key)  # read-only lookup for capability metadata
    if key in ctx.provider_cache:
        return ctx.provider_cache[key]
    provider = get_provider(key, ctx.config)
    ctx.provider_cache[key] = provider
    return provider


def _seed_from_structured_input(input_structured: object | None) -> int | None:
    if not isinstance(input_structured, dict):
        return None
    value = input_structured.get("seed")
    if isinstance(value, int) and value >= 0:
        return value
    return None


__all__ = ["_resolve_provider", "_seed_from_structured_input"]
