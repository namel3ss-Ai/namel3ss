from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message


REGISTRY_ENTRY_SCHEMA_PATH = Path(__file__).resolve().parents[4] / "resources" / "registry_entry_v1.json"
REQUIRED_FIELDS = {
    "entry_version",
    "pack_id",
    "pack_name",
    "pack_version",
    "pack_digest",
    "verified_by",
    "tools",
    "intent_tags",
    "intent_phrases",
    "capabilities",
    "runner",
    "source",
}


@dataclass(frozen=True)
class RegistryEntry:
    entry_version: int
    pack_id: str
    pack_name: str
    pack_version: str
    pack_digest: str
    signer_id: str | None
    verified_by: list[str]
    tools: list[str]
    intent_tags: list[str]
    intent_phrases: list[str]
    capabilities: dict[str, object]
    runner: dict[str, object]
    source: dict[str, object]
    guarantees: dict[str, object] | None = None

    def to_dict(self) -> dict[str, object]:
        payload = {
            "entry_version": self.entry_version,
            "pack_id": self.pack_id,
            "pack_name": self.pack_name,
            "pack_version": self.pack_version,
            "pack_digest": self.pack_digest,
            "signer_id": self.signer_id,
            "verified_by": list(self.verified_by),
            "tools": list(self.tools),
            "intent_tags": list(self.intent_tags),
            "intent_phrases": list(self.intent_phrases),
            "capabilities": dict(self.capabilities),
            "runner": dict(self.runner),
            "source": dict(self.source),
        }
        if self.guarantees is not None:
            payload["guarantees"] = dict(self.guarantees)
        return normalize_registry_entry(payload)


def load_registry_entry_schema(path: Path | None = None) -> dict:
    target = path or REGISTRY_ENTRY_SCHEMA_PATH
    if not target.exists():
        raise Namel3ssError(
            build_guidance_message(
                what="Registry entry schema is missing.",
                why=f"Expected {target.as_posix()} to exist.",
                fix="Restore resources/registry_entry_v1.json.",
                example="resources/registry_entry_v1.json",
            )
        )
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError as err:
        raise Namel3ssError(
            build_guidance_message(
                what="Registry entry schema is invalid JSON.",
                why=f"JSON parsing failed: {err.msg}.",
                fix="Fix the schema JSON.",
                example='{"entry_version": 1}',
            )
        ) from err
    if not isinstance(data, dict):
        raise Namel3ssError(
            build_guidance_message(
                what="Registry entry schema is invalid.",
                why="Expected a JSON object at the top level.",
                fix="Replace the schema with a JSON object.",
                example='{"type": "object"}',
            )
        )
    return data


def normalize_registry_entry(data: dict[str, object]) -> dict[str, object]:
    normalized = dict(data)
    for key in ("tools", "intent_tags", "intent_phrases", "verified_by"):
        value = normalized.get(key)
        if isinstance(value, list):
            normalized[key] = sorted(str(item) for item in value)
    capabilities = normalized.get("capabilities")
    if isinstance(capabilities, dict):
        secrets = capabilities.get("secrets")
        if isinstance(secrets, list):
            capabilities = dict(capabilities)
            capabilities["secrets"] = sorted(str(item) for item in secrets)
            normalized["capabilities"] = capabilities
    guarantees = normalized.get("guarantees")
    if isinstance(guarantees, dict):
        secrets = guarantees.get("secrets_allowed")
        if isinstance(secrets, list):
            guarantees = dict(guarantees)
            guarantees["secrets_allowed"] = sorted(str(item) for item in secrets)
            normalized["guarantees"] = guarantees
    return normalized


def validate_registry_entry(data: dict[str, object]) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["registry entry must be a JSON object"]
    missing = sorted(REQUIRED_FIELDS - set(data.keys()))
    if missing:
        errors.append(f"missing required fields: {', '.join(missing)}")
        return errors
    if not _is_int(data.get("entry_version")):
        errors.append("entry_version must be an integer")
    elif data.get("entry_version") != 1:
        errors.append("entry_version must be 1")
    for key in ("pack_id", "pack_name", "pack_version", "pack_digest"):
        if not _is_str(data.get(key)):
            errors.append(f"{key} must be a string")
    signer = data.get("signer_id")
    if signer is not None and not _is_str(signer):
        errors.append("signer_id must be a string or null")
    if not _is_str_list(data.get("verified_by")):
        errors.append("verified_by must be a list of strings")
    for key in ("tools", "intent_tags", "intent_phrases"):
        if not _is_str_list(data.get(key)):
            errors.append(f"{key} must be a list of strings")
    capabilities = data.get("capabilities")
    if not isinstance(capabilities, dict):
        errors.append("capabilities must be an object")
    else:
        errors.extend(_validate_capabilities(capabilities))
    guarantees = data.get("guarantees")
    if guarantees is not None:
        if not isinstance(guarantees, dict):
            errors.append("guarantees must be an object when provided")
        else:
            errors.extend(_validate_guarantees(guarantees))
    runner = data.get("runner")
    if not isinstance(runner, dict):
        errors.append("runner must be an object")
    else:
        errors.extend(_validate_runner(runner))
    source = data.get("source")
    if not isinstance(source, dict):
        errors.append("source must be an object")
    else:
        errors.extend(_validate_source(source))
    return errors


def _validate_capabilities(capabilities: dict[str, object]) -> list[str]:
    errors: list[str] = []
    for key in ("filesystem", "network", "env", "subprocess"):
        if not _is_str(capabilities.get(key)):
            errors.append(f"capabilities.{key} must be a string")
    secrets = capabilities.get("secrets")
    if not _is_str_list(secrets):
        errors.append("capabilities.secrets must be a list of strings")
    return errors


def _validate_guarantees(guarantees: dict[str, object]) -> list[str]:
    errors: list[str] = []
    for key in (
        "no_filesystem_write",
        "no_filesystem_read",
        "no_network",
        "no_subprocess",
        "no_env_read",
        "no_env_write",
    ):
        value = guarantees.get(key)
        if not isinstance(value, bool):
            errors.append(f"guarantees.{key} must be a boolean")
    secrets = guarantees.get("secrets_allowed")
    if secrets is not None and not _is_str_list(secrets):
        errors.append("guarantees.secrets_allowed must be a list of strings")
    return errors


def _validate_runner(runner: dict[str, object]) -> list[str]:
    errors: list[str] = []
    default = runner.get("default")
    if not _is_str(default):
        errors.append("runner.default must be a string")
    for key in ("service_url", "container_image"):
        value = runner.get(key)
        if value is not None and not _is_str(value):
            errors.append(f"runner.{key} must be a string or null")
    return errors


def _validate_source(source: dict[str, object]) -> list[str]:
    errors: list[str] = []
    kind = source.get("kind")
    uri = source.get("uri")
    if not _is_str(kind):
        errors.append("source.kind must be a string")
    if not _is_str(uri):
        errors.append("source.uri must be a string")
    return errors


def _is_str(value: object) -> bool:
    return isinstance(value, str) and value.strip() != ""


def _is_int(value: object) -> bool:
    return isinstance(value, int)


def _is_str_list(value: object) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) and item for item in value)


__all__ = [
    "REGISTRY_ENTRY_SCHEMA_PATH",
    "RegistryEntry",
    "load_registry_entry_schema",
    "normalize_registry_entry",
    "validate_registry_entry",
]
