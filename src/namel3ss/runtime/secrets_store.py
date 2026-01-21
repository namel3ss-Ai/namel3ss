from __future__ import annotations

import json
import os
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.persistence_paths import resolve_persistence_root


SECRET_ENV_PREFIXES = ("N3_SECRET_", "NAMEL3SS_SECRET_")
SECRETS_FILENAME = "secrets.json"


class SecretValue(str):
    def __new__(cls, redacted: str, *, secret_names: tuple[str, ...], secret_value: str):
        obj = super().__new__(cls, redacted)
        obj.secret_names = secret_names
        obj.secret_value = secret_value
        return obj


def resolve_secret_value(name: str, *, project_root: str | None, app_path: str | None) -> tuple[str, str]:
    normalized = normalize_secret_name(name)
    if not normalized:
        raise Namel3ssError(
            build_guidance_message(
                what="Secret name is empty.",
                why="Secrets must be referenced by a stable name.",
                fix="Use a short lowercase name.",
                example='secret("stripe_key")',
            )
        )
    env_key = _env_key_for(normalized)
    env_value = _read_env_value(env_key)
    if env_value is not None:
        return normalized, env_value
    secrets = _load_secret_file(project_root=project_root, app_path=app_path)
    value = secrets.get(normalized)
    if value is None:
        raise Namel3ssError(
            build_guidance_message(
                what=f"Secret '{normalized}' is missing.",
                why="Secrets are loaded from environment variables or a local secrets file.",
                fix=f"Set {env_key} or add the key to .namel3ss/{SECRETS_FILENAME}.",
                example=f'{env_key}="..."',
            )
        )
    return normalized, value


def normalize_secret_name(name: str) -> str:
    raw = (name or "").strip().lower()
    if not raw:
        return ""
    cleaned = []
    for ch in raw:
        if ch.isalnum() or ch in {"_", "-"}:
            cleaned.append(ch)
        else:
            cleaned.append("_")
    normalized = "".join(cleaned).strip("_-")
    while "__" in normalized:
        normalized = normalized.replace("__", "_")
    return normalized


def _env_key_for(name: str) -> str:
    env_name = name.upper().replace("-", "_")
    return f"{SECRET_ENV_PREFIXES[0]}{env_name}"


def _read_env_value(primary_key: str) -> str | None:
    value = os.getenv(primary_key)
    if value:
        return value
    for prefix in SECRET_ENV_PREFIXES[1:]:
        alt_key = f"{prefix}{primary_key[len(SECRET_ENV_PREFIXES[0]):]}"
        alt_value = os.getenv(alt_key)
        if alt_value:
            return alt_value
    return None


def _load_secret_file(*, project_root: str | None, app_path: str | None) -> dict[str, str]:
    root = resolve_persistence_root(project_root, app_path, allow_create=False)
    if root is None:
        return {}
    path = Path(root) / ".namel3ss" / SECRETS_FILENAME
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise Namel3ssError(
            build_guidance_message(
                what=f".namel3ss/{SECRETS_FILENAME} is not valid JSON.",
                why="Secrets files must contain a JSON object.",
                fix="Fix the JSON syntax or remove the file.",
                example='{"stripe_key": "sk_test_..."}',
            )
        ) from exc
    secrets = raw.get("secrets") if isinstance(raw, dict) else None
    if secrets is None:
        secrets = raw if isinstance(raw, dict) else {}
    if not isinstance(secrets, dict):
        return {}
    normalized: dict[str, str] = {}
    for key, value in secrets.items():
        if not isinstance(key, str) or not isinstance(value, str):
            continue
        normalized_name = normalize_secret_name(key)
        if normalized_name:
            normalized[normalized_name] = value
    return normalized


__all__ = ["SECRET_ENV_PREFIXES", "SECRETS_FILENAME", "SecretValue", "normalize_secret_name", "resolve_secret_value"]
