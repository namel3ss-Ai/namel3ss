from __future__ import annotations

from importlib import import_module

from namel3ss.runtime.ai.providers.registry import get_provider as _default_get_provider
from namel3ss.runtime.executor.context import ExecutionContext
from namel3ss.runtime.providers.capabilities import (
    get_provider_capabilities as _default_get_provider_capabilities,
)


def _resolve_provider_functions():
    module = import_module("namel3ss.runtime.executor.ai_runner")
    get_provider_fn = getattr(module, "get_provider", _default_get_provider)
    get_capabilities_fn = getattr(
        module,
        "get_provider_capabilities",
        _default_get_provider_capabilities,
    )
    return get_provider_fn, get_capabilities_fn


def _resolve_provider_capabilities(provider_name: str):
    _, get_capabilities_fn = _resolve_provider_functions()
    return get_capabilities_fn(provider_name.lower())


def _resolve_provider(ctx: ExecutionContext, provider_name: str):
    key = provider_name.lower()
    _ = _resolve_provider_capabilities(key)  # read-only lookup for capability metadata
    if key in ctx.provider_cache:
        return ctx.provider_cache[key]
    get_provider_fn, _ = _resolve_provider_functions()
    provider = get_provider_fn(key, ctx.config)
    ctx.provider_cache[key] = provider
    return provider


def _seed_from_structured_input(input_structured: object | None) -> int | None:
    if not isinstance(input_structured, dict):
        return None
    value = input_structured.get("seed")
    if isinstance(value, int) and value >= 0:
        return value
    return None


__all__ = [
    "_resolve_provider",
    "_resolve_provider_capabilities",
    "_seed_from_structured_input",
]
