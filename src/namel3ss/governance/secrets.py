from __future__ import annotations

import base64
import hashlib
import os
import json
from dataclasses import dataclass
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.governance.paths import governance_file
from namel3ss.security_encryption import EncryptionService
from namel3ss.utils.json_tools import dumps as json_dumps


VAULT_FILENAME = "secrets.json"
MASTER_KEY_FILENAME = "master.key"


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


@dataclass(frozen=True)
class SecretEntry:
    name: str
    encrypted_value: str
    created_at: int
    owner: str

    def to_public_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "created_at": self.created_at,
            "owner": self.owner,
        }


@dataclass(frozen=True)
class SecretVault:
    entries: tuple[SecretEntry, ...]

    def by_name(self) -> dict[str, SecretEntry]:
        return {entry.name: entry for entry in self.entries}



def master_key_path() -> Path:
    return Path.home() / ".namel3ss" / MASTER_KEY_FILENAME



def ensure_master_key() -> Path:
    path = master_key_path()
    if path.exists():
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = os.urandom(32)
    encoded = base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
    path.write_text(encoded, encoding="utf-8")
    return path



def vault_path(project_root: str | Path | None, app_path: str | Path | None) -> Path | None:
    return governance_file(project_root, app_path, VAULT_FILENAME)



def list_secrets(project_root: str | Path | None, app_path: str | Path | None) -> list[dict[str, object]]:
    vault = load_vault(project_root, app_path)
    rows = [entry.to_public_dict() for entry in vault.entries]
    rows.sort(key=lambda item: str(item.get("name") or ""))
    return rows



def add_secret(
    *,
    project_root: str | Path | None,
    app_path: str | Path | None,
    name: str,
    value: str,
    owner: str,
) -> tuple[Path, SecretEntry]:
    normalized = normalize_secret_name(name)
    if not normalized:
        raise Namel3ssError(_invalid_name_message())
    if not isinstance(value, str) or value == "":
        raise Namel3ssError(_invalid_value_message())
    path = vault_path(project_root, app_path)
    if path is None:
        raise Namel3ssError("Secrets vault path could not be resolved.")

    service = _load_encryption_service(required=True)
    encrypted = service.encrypt_text(value)

    vault = load_vault(project_root, app_path)
    current = vault.by_name()
    previous = current.get(normalized)
    created_at = previous.created_at if previous is not None else _next_created_at(vault.entries)
    entry = SecretEntry(
        name=normalized,
        encrypted_value=encrypted,
        created_at=created_at,
        owner=(owner or "system").strip() or "system",
    )
    current[normalized] = entry
    _write_vault(path, current)
    return path, entry



def get_secret(
    *,
    project_root: str | Path | None,
    app_path: str | Path | None,
    name: str,
) -> str:
    normalized = normalize_secret_name(name)
    if not normalized:
        raise Namel3ssError(_invalid_name_message())
    vault = load_vault(project_root, app_path)
    entry = vault.by_name().get(normalized)
    if entry is None:
        raise Namel3ssError(_missing_secret_message(normalized))
    service = _load_encryption_service(required=True)
    return service.decrypt_text(entry.encrypted_value)



def remove_secret(
    *,
    project_root: str | Path | None,
    app_path: str | Path | None,
    name: str,
) -> tuple[Path, dict[str, object]]:
    normalized = normalize_secret_name(name)
    if not normalized:
        raise Namel3ssError(_invalid_name_message())
    path = vault_path(project_root, app_path)
    if path is None:
        raise Namel3ssError("Secrets vault path could not be resolved.")
    entries = load_vault(project_root, app_path).by_name()
    entry = entries.get(normalized)
    if entry is None:
        raise Namel3ssError(_missing_secret_message(normalized))
    del entries[normalized]
    _write_vault(path, entries)
    return path, entry.to_public_dict()


def load_decrypted_secrets_map(project_root: str | Path | None, app_path: str | Path | None) -> dict[str, str]:
    vault = load_vault(project_root, app_path)
    if not vault.entries:
        return {}
    service = _load_encryption_service(required=True)
    values: dict[str, str] = {}
    for entry in vault.entries:
        values[entry.name] = service.decrypt_text(entry.encrypted_value)
    return values



def load_vault(project_root: str | Path | None, app_path: str | Path | None) -> SecretVault:
    path = vault_path(project_root, app_path)
    if path is None or not path.exists():
        return SecretVault(entries=())
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as err:
        raise Namel3ssError(_invalid_vault_message(path)) from err
    if not isinstance(payload, dict):
        raise Namel3ssError(_invalid_vault_message(path))
    raw_secrets = payload.get("secrets")
    if raw_secrets is None:
        raw_secrets = payload
    if not isinstance(raw_secrets, dict):
        raise Namel3ssError(_invalid_vault_message(path))
    entries: list[SecretEntry] = []
    for key in sorted(raw_secrets.keys(), key=lambda item: str(item)):
        normalized = normalize_secret_name(str(key))
        if not normalized:
            continue
        raw = raw_secrets[key]
        if isinstance(raw, str) and raw:
            # Backward compatibility with legacy plain-value secrets.json
            service = _load_encryption_service(required=True)
            encrypted = service.encrypt_text(raw)
            entries.append(
                SecretEntry(name=normalized, encrypted_value=encrypted, created_at=len(entries) + 1, owner="legacy")
            )
            continue
        if not isinstance(raw, dict):
            continue
        encrypted = raw.get("encrypted_value")
        if not isinstance(encrypted, str) or not encrypted:
            continue
        created_at = raw.get("created_at")
        owner = raw.get("owner")
        entries.append(
            SecretEntry(
                name=normalized,
                encrypted_value=encrypted,
                created_at=_coerce_int(created_at, default=len(entries) + 1),
                owner=str(owner).strip() if isinstance(owner, str) and owner.strip() else "system",
            )
        )
    entries.sort(key=lambda entry: entry.name)
    return SecretVault(entries=tuple(entries))



def _write_vault(path: Path, values: dict[str, SecretEntry]) -> None:
    payload = {
        "schema_version": 1,
        "secrets": {
            name: {
                "encrypted_value": entry.encrypted_value,
                "created_at": int(entry.created_at),
                "owner": entry.owner,
            }
            for name, entry in sorted(values.items(), key=lambda item: item[0])
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json_dumps(payload), encoding="utf-8")



def _load_encryption_service(*, required: bool) -> EncryptionService:
    key_path = ensure_master_key() if required else master_key_path()
    if not key_path.exists():
        raise Namel3ssError(_missing_master_key_message(key_path))
    raw = key_path.read_text(encoding="utf-8").strip()
    if not raw:
        raise Namel3ssError(_missing_master_key_message(key_path))
    try:
        padded = raw + "=" * ((4 - len(raw) % 4) % 4)
        decoded = base64.urlsafe_b64decode(padded.encode("ascii"))
    except Exception:
        try:
            decoded = bytes.fromhex(raw)
        except Exception as err:
            raise Namel3ssError(_invalid_master_key_message(key_path)) from err
    key = hashlib.sha256(decoded).digest()
    return EncryptionService(key=key)



def _coerce_int(value: object, *, default: int) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return default



def _next_created_at(entries: tuple[SecretEntry, ...]) -> int:
    if not entries:
        return 1
    return max(entry.created_at for entry in entries) + 1



def _invalid_name_message() -> str:
    return build_guidance_message(
        what="Secret name is invalid.",
        why="Secret names must contain letters, numbers, underscore, or dash.",
        fix="Use a stable secret name.",
        example="n3 secret add db_password value",
    )



def _invalid_value_message() -> str:
    return build_guidance_message(
        what="Secret value is invalid.",
        why="Secret value cannot be empty.",
        fix="Provide a non-empty secret value.",
        example="n3 secret add db_password supersecret",
    )



def _missing_secret_message(name: str) -> str:
    return build_guidance_message(
        what=f"Secret '{name}' is missing.",
        why="The secret was not found in the encrypted vault.",
        fix="Add the secret first.",
        example=f"n3 secret add {name} value",
    )



def _invalid_vault_message(path: Path) -> str:
    return build_guidance_message(
        what="Secrets vault is invalid.",
        why=f"Could not parse {path.as_posix()}.",
        fix="Repair the JSON file or recreate it with n3 secret add.",
        example='{"schema_version":1,"secrets":{}}',
    )



def _missing_master_key_message(path: Path) -> str:
    return build_guidance_message(
        what="Master key is missing.",
        why=f"Expected key at {path.as_posix()}.",
        fix="Create the key with n3 secret add, which auto-initializes the key.",
        example="~/.namel3ss/master.key",
    )



def _invalid_master_key_message(path: Path) -> str:
    return build_guidance_message(
        what="Master key is invalid.",
        why=f"Could not decode key at {path.as_posix()}.",
        fix="Replace it with base64 or hex bytes.",
        example="python3 -c \"import os,base64;print(base64.urlsafe_b64encode(os.urandom(32)).decode().rstrip('='))\"",
    )


__all__ = [
    "SecretEntry",
    "SecretVault",
    "VAULT_FILENAME",
    "add_secret",
    "ensure_master_key",
    "get_secret",
    "list_secrets",
    "load_decrypted_secrets_map",
    "load_vault",
    "master_key_path",
    "remove_secret",
    "vault_path",
]
