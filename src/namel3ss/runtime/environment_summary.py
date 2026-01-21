from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from namel3ss.config.dotenv import load_dotenv_for_path
from namel3ss.config.env_loader import (
    ENV_AUTH_ALLOW_IDENTITY,
    ENV_AUTH_CREDENTIALS_JSON,
    ENV_AUTH_IDENTITY_JSON,
    ENV_AUTH_PASSWORD,
    ENV_AUTH_SIGNING_KEY,
    ENV_AUTH_USERNAME,
    ENV_IDENTITY_JSON,
    ENV_IDENTITY_PREFIX,
)
from namel3ss.config.loader import ConfigSource, resolve_config
from namel3ss.config.model import AppConfig
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.persistence_paths import ENV_PERSIST_ROOT
from namel3ss.runtime.secrets_store import SECRET_ENV_PREFIXES, list_secret_keys
from namel3ss.secrets import discover_required_secrets
from namel3ss.utils.path_display import display_path_hint


@dataclass(frozen=True)
class EnvSpec:
    name: str
    purpose: str


_PROVIDER_FIELDS: dict[str, tuple[str, str, str]] = {
    "NAMEL3SS_OPENAI_API_KEY": ("openai", "api_key", "OpenAI provider"),
    "NAMEL3SS_ANTHROPIC_API_KEY": ("anthropic", "api_key", "Anthropic provider"),
    "NAMEL3SS_GEMINI_API_KEY": ("gemini", "api_key", "Gemini provider"),
    "NAMEL3SS_MISTRAL_API_KEY": ("mistral", "api_key", "Mistral provider"),
}

_PROVIDER_ALIASES: dict[str, tuple[str, ...]] = {
    "NAMEL3SS_OPENAI_API_KEY": ("OPENAI_API_KEY",),
    "NAMEL3SS_ANTHROPIC_API_KEY": ("ANTHROPIC_API_KEY",),
    "NAMEL3SS_GEMINI_API_KEY": ("GEMINI_API_KEY", "GOOGLE_API_KEY"),
    "NAMEL3SS_MISTRAL_API_KEY": ("MISTRAL_API_KEY",),
}

_PERSISTENCE_FIELDS: dict[str, tuple[str, str]] = {
    "N3_DATABASE_URL": ("database_url", "Postgres persistence"),
    "N3_EDGE_KV_URL": ("edge_kv_url", "Edge persistence"),
}

_OPTIONAL_SPECS = [
    EnvSpec("NAMEL3SS_OLLAMA_HOST", "Ollama host URL"),
    EnvSpec("NAMEL3SS_OLLAMA_TIMEOUT_SECONDS", "Ollama timeout seconds"),
    EnvSpec("NAMEL3SS_OPENAI_API_KEY", "OpenAI provider key"),
    EnvSpec("NAMEL3SS_OPENAI_BASE_URL", "OpenAI base URL"),
    EnvSpec("NAMEL3SS_ANTHROPIC_API_KEY", "Anthropic provider key"),
    EnvSpec("NAMEL3SS_GEMINI_API_KEY", "Gemini provider key"),
    EnvSpec("NAMEL3SS_MISTRAL_API_KEY", "Mistral provider key"),
    EnvSpec("N3_PERSIST_TARGET", "Persistence target"),
    EnvSpec("N3_PERSIST", "Enable persistence"),
    EnvSpec("N3_DB_PATH", "SQLite database path"),
    EnvSpec("N3_DATABASE_URL", "Database URL"),
    EnvSpec("N3_EDGE_KV_URL", "Edge KV URL"),
    EnvSpec("N3_REPLICA_URLS", "Replica URLs"),
    EnvSpec(ENV_PERSIST_ROOT, "Persistence root path"),
    EnvSpec("N3_PYTHON_TOOL_TIMEOUT_SECONDS", "Python tool timeout seconds"),
    EnvSpec("N3_TOOL_SERVICE_URL", "Tool service URL"),
    EnvSpec("N3_FOREIGN_STRICT", "Foreign tool strict mode"),
    EnvSpec("N3_FOREIGN_ALLOW", "Foreign tool allow mode"),
    EnvSpec(ENV_IDENTITY_JSON, "Identity defaults JSON"),
    EnvSpec(ENV_AUTH_SIGNING_KEY, "Authentication signing key"),
    EnvSpec(ENV_AUTH_ALLOW_IDENTITY, "Authentication identity allowlist"),
    EnvSpec(ENV_AUTH_USERNAME, "Authentication username"),
    EnvSpec(ENV_AUTH_PASSWORD, "Authentication password"),
    EnvSpec(ENV_AUTH_IDENTITY_JSON, "Authentication identity JSON"),
    EnvSpec(ENV_AUTH_CREDENTIALS_JSON, "Authentication credentials JSON"),
    EnvSpec("N3_VERIFY_ON_SHIP", "Verify during ship"),
]


def build_environment_summary(
    project_root: str | Path | None,
    app_path: str | Path | None,
    *,
    program: object | None = None,
    config: AppConfig | None = None,
    sources: list[ConfigSource] | None = None,
    target: str | None = None,
) -> dict:
    root_path = _coerce_path(project_root)
    app_file = _coerce_path(app_path)
    if config is None or sources is None:
        config, sources = resolve_config(app_path=app_file, root=root_path)
    dotenv_values = load_dotenv_for_path(app_file.as_posix()) if app_file else {}
    env_keys = set(os.environ.keys())
    secret_keys = set(list_secret_keys(project_root=str(root_path) if root_path else None, app_path=app_path))
    required = _required_entries(
        program,
        config,
        env_keys=env_keys,
        dotenv_values=dotenv_values,
        secret_keys=secret_keys,
        target=target or "local",
        app_path=app_file,
    )
    required_names = {entry["name"] for entry in required}
    optional = _optional_entries(env_keys=env_keys, dotenv_values=dotenv_values, skip=required_names)
    overrides = [entry["name"] for entry in optional if entry.get("status") == "set"]
    missing = [entry["name"] for entry in required if entry.get("status") == "missing"]
    guidance = _guidance_for_missing(required)
    payload = {
        "ok": True,
        "sources": _render_sources(sources, root_path),
        "summary": {
            "required": len(required),
            "missing": len(missing),
            "optional": len(optional),
            "overrides": len(overrides),
        },
        "required": required,
        "optional": optional,
        "overrides": overrides,
        "missing": missing,
    }
    if guidance:
        payload["guidance"] = guidance
    return payload


def _required_entries(
    program: object | None,
    config: AppConfig,
    *,
    env_keys: set[str],
    dotenv_values: dict[str, str],
    secret_keys: set[str],
    target: str,
    app_path: Path | None,
) -> list[dict]:
    required = discover_required_secrets(program, config, target=target, app_path=app_path)
    entries: list[dict] = []
    for ref in required:
        name = ref.name
        if name in _PROVIDER_FIELDS:
            entries.append(_provider_entry(name, config, env_keys, dotenv_values))
        elif name in _PERSISTENCE_FIELDS:
            entries.append(_persistence_entry(name, config, env_keys, dotenv_values))
        else:
            entries.append(_custom_secret_entry(name, env_keys, dotenv_values, secret_keys))
    return sorted(entries, key=lambda item: item["name"])


def _provider_entry(
    name: str,
    config: AppConfig,
    env_keys: set[str],
    dotenv_values: dict[str, str],
) -> dict:
    provider, field, label = _PROVIDER_FIELDS.get(name, ("", "", "Provider"))
    config_value = getattr(getattr(config, provider, object()), field, None)
    if config_value:
        return {
            "name": name,
            "status": "set",
            "source": "config",
            "kind": "provider",
            "reason": label,
        }
    alias_keys = _PROVIDER_ALIASES.get(name, ())
    source = _env_source(name, alias_keys=alias_keys, env_keys=env_keys, dotenv_values=dotenv_values, require_value=True)
    status = "set" if source != "missing" else "missing"
    return {
        "name": name,
        "status": status,
        "source": source,
        "kind": "provider",
        "reason": label,
    }


def _persistence_entry(
    name: str,
    config: AppConfig,
    env_keys: set[str],
    dotenv_values: dict[str, str],
) -> dict:
    field, label = _PERSISTENCE_FIELDS.get(name, ("", "Persistence"))
    config_value = getattr(getattr(config, "persistence", object()), field, None)
    if config_value:
        return {
            "name": name,
            "status": "set",
            "source": "config",
            "kind": "persistence",
            "reason": label,
        }
    source = _env_source(name, env_keys=env_keys, dotenv_values=dotenv_values, require_value=True)
    status = "set" if source != "missing" else "missing"
    return {
        "name": name,
        "status": status,
        "source": source,
        "kind": "persistence",
        "reason": label,
    }


def _custom_secret_entry(
    name: str,
    env_keys: set[str],
    dotenv_values: dict[str, str],
    secret_keys: set[str],
) -> dict:
    suffix = name.upper().replace("-", "_")
    env_names = tuple(f"{prefix}{suffix}" for prefix in SECRET_ENV_PREFIXES)
    source = _env_source(env_names[0], alias_keys=env_names[1:], env_keys=env_keys, dotenv_values=dotenv_values, require_value=True)
    if source != "missing":
        status = "set"
    elif name in secret_keys:
        source = "secrets_file"
        status = "set"
    else:
        status = "missing"
    return {
        "name": env_names[0],
        "status": status,
        "source": source,
        "kind": "secret",
        "reason": "Secret call",
        "secret_name": name,
    }


def _optional_entries(
    *,
    env_keys: set[str],
    dotenv_values: dict[str, str],
    skip: set[str],
) -> list[dict]:
    entries: list[dict] = []
    identity_fields = _identity_fields(env_keys, dotenv_values)
    if identity_fields:
        entries.append(
            {
                "name": f"{ENV_IDENTITY_PREFIX}*",
                "status": "set",
                "source": "env" if _has_env_prefix(env_keys) else "dotenv",
                "purpose": "Identity field overrides",
                "fields": identity_fields,
            }
        )
    elif f"{ENV_IDENTITY_PREFIX}*" not in skip:
        entries.append(
            {
                "name": f"{ENV_IDENTITY_PREFIX}*",
                "status": "unset",
                "source": "missing",
                "purpose": "Identity field overrides",
                "fields": [],
            }
        )
    for spec in _OPTIONAL_SPECS:
        if spec.name in skip:
            continue
        source = _env_presence(spec.name, env_keys=env_keys, dotenv_values=dotenv_values)
        status = "set" if source != "missing" else "unset"
        entries.append({"name": spec.name, "status": status, "source": source, "purpose": spec.purpose})
    return sorted(entries, key=lambda item: item["name"])


def _identity_fields(env_keys: set[str], dotenv_values: dict[str, str]) -> list[str]:
    keys = {key for key in env_keys if key.startswith(ENV_IDENTITY_PREFIX) and key != ENV_IDENTITY_JSON}
    keys.update({key for key in dotenv_values if key.startswith(ENV_IDENTITY_PREFIX) and key != ENV_IDENTITY_JSON})
    fields = []
    for key in sorted(keys):
        field = key[len(ENV_IDENTITY_PREFIX) :].strip().lower()
        if field:
            fields.append(field)
    return fields


def _has_env_prefix(env_keys: set[str]) -> bool:
    return any(key.startswith(ENV_IDENTITY_PREFIX) for key in env_keys if key != ENV_IDENTITY_JSON)


def _guidance_for_missing(entries: list[dict]) -> list[str]:
    guidance: list[str] = []
    for entry in entries:
        if entry.get("status") != "missing":
            continue
        kind = entry.get("kind")
        name = entry.get("name", "unknown")
        if kind == "provider":
            guidance.append(
                build_guidance_message(
                    what=f"Missing {name}.",
                    why=f"{entry.get('reason', 'Provider')} is referenced by this app.",
                    fix="Set the value in namel3ss.toml, .env, or the environment.",
                    example=f'{name}="..."',
                )
            )
        elif kind == "persistence":
            guidance.append(
                build_guidance_message(
                    what=f"Missing {name}.",
                    why=f"{entry.get('reason', 'Persistence')} requires this value.",
                    fix="Set it in namel3ss.toml, .env, or the environment.",
                    example=f'{name}="..."',
                )
            )
        elif kind == "secret":
            secret_name = entry.get("secret_name", "secret")
            guidance.append(
                build_guidance_message(
                    what=f"Secret '{secret_name}' is missing.",
                    why="Secrets are required by the program.",
                    fix=f"Set {name} or add '{secret_name}' to .namel3ss/secrets.json.",
                    example=f'{name}="..."',
                )
            )
    return guidance


def _env_source(
    name: str,
    *,
    alias_keys: tuple[str, ...] = (),
    env_keys: set[str],
    dotenv_values: dict[str, str],
    require_value: bool,
) -> str:
    if name in env_keys:
        value = os.getenv(name)
        if value or not require_value:
            return "env"
    for alias in alias_keys:
        if alias in env_keys:
            value = os.getenv(alias)
            if value or not require_value:
                return "env"
    if name in dotenv_values:
        value = dotenv_values.get(name)
        if value or not require_value:
            return "dotenv"
    for alias in alias_keys:
        if alias in dotenv_values:
            value = dotenv_values.get(alias)
            if value or not require_value:
                return "dotenv"
    return "missing"


def _env_presence(name: str, *, env_keys: set[str], dotenv_values: dict[str, str]) -> str:
    if name in dotenv_values:
        return "dotenv"
    if name in env_keys:
        return "env"
    return "missing"


def _render_sources(sources: list[ConfigSource], project_root: Path | None) -> list[dict]:
    rendered: list[dict] = []
    for source in sources:
        entry = {"kind": source.kind}
        if source.path:
            base = project_root if project_root else Path.cwd()
            entry["path"] = display_path_hint(source.path, base=base)
        rendered.append(entry)
    return rendered


def _coerce_path(value: str | Path | None) -> Path | None:
    if value is None:
        return None
    return Path(value)


__all__ = ["build_environment_summary"]
