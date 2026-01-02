from __future__ import annotations

from pathlib import Path
from typing import Iterable

from namel3ss.config.dotenv import load_dotenv_for_path
from namel3ss.config.model import AppConfig
from namel3ss.ir import nodes as ir
from namel3ss.secrets.model import SecretRef


PROVIDER_ENV = {
    "openai": "NAMEL3SS_OPENAI_API_KEY",
    "anthropic": "NAMEL3SS_ANTHROPIC_API_KEY",
    "gemini": "NAMEL3SS_GEMINI_API_KEY",
    "mistral": "NAMEL3SS_MISTRAL_API_KEY",
}

_ENV_ALIASES: dict[str, tuple[str, ...]] = {
    "NAMEL3SS_OPENAI_API_KEY": ("OPENAI_API_KEY",),
    "NAMEL3SS_ANTHROPIC_API_KEY": ("ANTHROPIC_API_KEY",),
    "NAMEL3SS_GEMINI_API_KEY": ("GEMINI_API_KEY", "GOOGLE_API_KEY"),
    "NAMEL3SS_MISTRAL_API_KEY": ("MISTRAL_API_KEY",),
}


def discover_required_secrets(
    program: ir.Program | None,
    config: AppConfig,
    *,
    target: str,
    app_path: Path | None,
) -> list[SecretRef]:
    dotenv_values = _load_dotenv(app_path)
    required = _required_secret_names(program, config)
    return [_secret_ref(name, dotenv_values, target=target) for name in sorted(required)]


def discover_required_secrets_for_profiles(
    ai_profiles: dict[str, ir.AIDecl] | None,
    config: AppConfig,
    *,
    target: str,
    app_path: Path | None,
) -> list[SecretRef]:
    dotenv_values = _load_dotenv(app_path)
    providers = _providers_from_profiles(ai_profiles or {})
    required = _required_secret_names_for_providers(providers, config)
    return [_secret_ref(name, dotenv_values, target=target) for name in sorted(required)]


def _required_secret_names(program: ir.Program | None, config: AppConfig) -> set[str]:
    providers = _providers_from_program(program)
    return _required_secret_names_for_providers(providers, config)


def _required_secret_names_for_providers(providers: Iterable[str], config: AppConfig) -> set[str]:
    names: set[str] = set()
    for provider in providers:
        normalized = (provider or "").lower()
        if normalized in PROVIDER_ENV:
            names.add(PROVIDER_ENV[normalized])
    target = (config.persistence.target or "memory").lower()
    if target == "postgres":
        names.add("N3_DATABASE_URL")
    if target == "edge":
        names.add("N3_EDGE_KV_URL")
    return names


def _providers_from_program(program: ir.Program | None) -> list[str]:
    if program is None:
        return []
    return _providers_from_profiles(getattr(program, "ais", {}) or {})


def _providers_from_profiles(ai_profiles: dict[str, ir.AIDecl]) -> list[str]:
    providers: list[str] = []
    for ai in ai_profiles.values():
        provider = (getattr(ai, "provider", "") or "").lower()
        if provider:
            providers.append(provider)
    return providers


def _secret_ref(name: str, dotenv_values: dict[str, str], *, target: str) -> SecretRef:
    source = "missing"
    available = False
    aliases = _ENV_ALIASES.get(name, ())
    if name in dotenv_values or any(alias in dotenv_values for alias in aliases):
        source = "dotenv"
        available = True
    env_keys = _env_keys()
    if name in env_keys or any(alias in env_keys for alias in aliases):
        source = "env"
        available = True
    return SecretRef(name=name, source=source, target=target, available=available)


def _env_keys() -> set[str]:
    import os

    return set(os.environ.keys())


def _load_dotenv(app_path: Path | None) -> dict[str, str]:
    if app_path is None:
        return {}
    return load_dotenv_for_path(app_path.as_posix())


__all__ = ["discover_required_secrets", "discover_required_secrets_for_profiles", "PROVIDER_ENV"]
