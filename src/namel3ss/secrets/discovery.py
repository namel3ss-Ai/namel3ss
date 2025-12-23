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


def _required_secret_names(program: ir.Program | None, config: AppConfig) -> set[str]:
    names: set[str] = set()
    if program is not None:
        for ai in getattr(program, "ais", {}).values():
            provider = (getattr(ai, "provider", "") or "").lower()
            if provider in PROVIDER_ENV:
                names.add(PROVIDER_ENV[provider])
    target = (config.persistence.target or "memory").lower()
    if target == "postgres":
        names.add("N3_DATABASE_URL")
    if target == "edge":
        names.add("N3_EDGE_KV_URL")
    return names


def _secret_ref(name: str, dotenv_values: dict[str, str], *, target: str) -> SecretRef:
    source = "missing"
    available = False
    if name in dotenv_values:
        source = "dotenv"
        available = True
    if name in _env_keys():
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


__all__ = ["discover_required_secrets", "PROVIDER_ENV"]
