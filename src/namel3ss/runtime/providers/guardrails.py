from __future__ import annotations

from collections.abc import Mapping
import os

from namel3ss.config.model import AppConfig
from namel3ss.runtime.errors.classification import build_runtime_error


_REAL_API_PROVIDERS: tuple[str, ...] = ("openai", "anthropic", "gemini", "mistral")
_KNOWN_PROVIDERS: set[str] = {
    "mock",
    "ollama",
    "openai",
    "anthropic",
    "gemini",
    "mistral",
    "huggingface",
    "local_runner",
    "vision_gen",
    "speech",
    "third_party_apis",
}
_PROVIDER_LABELS = {
    "openai": "OpenAI",
    "anthropic": "Anthropic",
    "gemini": "Gemini",
    "mistral": "Mistral",
    "mock": "mock",
}
_ENV_KEYS = {
    "openai": ("NAMEL3SS_OPENAI_API_KEY", "OPENAI_API_KEY"),
    "anthropic": ("NAMEL3SS_ANTHROPIC_API_KEY", "ANTHROPIC_API_KEY"),
    "gemini": ("NAMEL3SS_GEMINI_API_KEY", "GEMINI_API_KEY"),
    "mistral": ("NAMEL3SS_MISTRAL_API_KEY", "MISTRAL_API_KEY"),
}


def provider_guardrail_diagnostics(
    config: AppConfig | None,
    *,
    env: Mapping[str, str] | None = None,
) -> list[dict[str, str]]:
    if config is None:
        return []
    env_map = env if isinstance(env, Mapping) else os.environ
    active = _active_provider(config)
    key_presence = _provider_keys_present(config, env_map)
    diagnostics: list[dict[str, str]] = []

    if active not in _KNOWN_PROVIDERS:
        diagnostics.append(
            build_runtime_error(
                "provider_misconfigured",
                message=f'Unknown answer provider "{active}".',
                hint="Set [answer].provider to a supported provider.",
                origin="provider",
                stable_code="runtime.provider_misconfigured.unknown_provider",
            )
        )

    configured_real = [name for name in _REAL_API_PROVIDERS if key_presence.get(name, False)]
    configured_real.sort()
    if active == "mock" and configured_real:
        first = configured_real[0]
        label = _PROVIDER_LABELS.get(first, first)
        diagnostics.append(
            build_runtime_error(
                "provider_mock_active",
                message=f"{label} key detected but provider is set to mock. Real AI calls are not active.",
                hint="Set [answer].provider to a real provider or remove unused keys.",
                origin="provider",
                stable_code=f"runtime.provider_mock_active.{first}",
            )
        )

    if active in _REAL_API_PROVIDERS and not key_presence.get(active, False):
        label = _PROVIDER_LABELS.get(active, active)
        diagnostics.append(
            build_runtime_error(
                "provider_misconfigured",
                message=f"{label} provider is selected but no API key is configured.",
                hint=f"Set the {label} API key in config or environment, then retry.",
                origin="provider",
                stable_code=f"runtime.provider_misconfigured.{active}.missing_key",
            )
        )

    return _dedupe_sorted(diagnostics)


def _active_provider(config: AppConfig) -> str:
    provider = str(getattr(getattr(config, "answer", None), "provider", "mock") or "mock")
    normalized = provider.strip().lower()
    return normalized or "mock"


def _provider_keys_present(config: AppConfig, env: Mapping[str, str]) -> dict[str, bool]:
    flags: dict[str, bool] = {}
    for provider in _REAL_API_PROVIDERS:
        flags[provider] = _provider_key_present(config, provider, env)
    return flags


def _provider_key_present(config: AppConfig, provider: str, env: Mapping[str, str]) -> bool:
    provider_config = getattr(config, provider, None)
    config_key = str(getattr(provider_config, "api_key", "") or "").strip()
    if config_key:
        return True
    env_keys = _ENV_KEYS.get(provider, ())
    for key in env_keys:
        value = str(env.get(key, "") or "").strip()
        if value:
            return True
    return False


def _dedupe_sorted(entries: list[dict[str, str]]) -> list[dict[str, str]]:
    deduped: dict[str, dict[str, str]] = {}
    for entry in entries:
        code = str(entry.get("stable_code") or "").strip()
        if not code or code in deduped:
            continue
        deduped[code] = entry
    return [deduped[key] for key in sorted(deduped)]


__all__ = ["provider_guardrail_diagnostics"]
