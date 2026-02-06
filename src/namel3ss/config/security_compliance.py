from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.utils.simple_yaml import parse_yaml

AUTH_FILENAME = "auth.yaml"
SECURITY_FILENAME = "security.yaml"
RETENTION_FILENAME = "retention.yaml"
_ALLOWED_LOGIN_METHODS = ("password", "bearer_token")

@dataclass(frozen=True)
class AuthConfig:
    version: str
    roles: dict[str, tuple[str, ...]]
    methods: dict[str, bool]

    def to_dict(self) -> dict[str, object]:
        return {
            "version": self.version,
            "roles": {
                role: {"permissions": list(self.roles[role])}
                for role in sorted(self.roles.keys())
            },
            "authentication": {
                "methods": {name: bool(self.methods[name]) for name in _ALLOWED_LOGIN_METHODS},
            },
        }

@dataclass(frozen=True)
class SecurityConfig:
    version: str
    encryption_enabled: bool
    encryption_algorithm: str
    encryption_key_ref: str
    max_memory_mb: int
    max_cpu_ms: int

    def to_dict(self) -> dict[str, object]:
        return {
            "version": self.version,
            "encryption": {
                "enabled": bool(self.encryption_enabled),
                "algorithm": self.encryption_algorithm,
                "key": self.encryption_key_ref,
            },
            "resource_limits": {
                "max_memory_mb": int(self.max_memory_mb),
                "max_cpu_ms": int(self.max_cpu_ms),
            },
        }

@dataclass(frozen=True)
class RetentionRecordRule:
    retention_days: int
    anonymize_fields: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "retention_days": int(self.retention_days),
            "anonymize_fields": list(self.anonymize_fields),
        }

@dataclass(frozen=True)
class RetentionConfig:
    version: str
    records: dict[str, RetentionRecordRule]
    audit_enabled: bool
    audit_retention_days: int

    def to_dict(self) -> dict[str, object]:
        return {
            "version": self.version,
            "records": {
                name: self.records[name].to_dict()
                for name in sorted(self.records.keys())
            },
            "audit": {
                "enabled": bool(self.audit_enabled),
                "retention_days": int(self.audit_retention_days),
            },
        }

def auth_config_path(project_root: str | Path | None, app_path: str | Path | None) -> Path | None:
    return _config_path(project_root, app_path, AUTH_FILENAME)

def security_config_path(project_root: str | Path | None, app_path: str | Path | None) -> Path | None:
    return _config_path(project_root, app_path, SECURITY_FILENAME)

def retention_config_path(project_root: str | Path | None, app_path: str | Path | None) -> Path | None:
    return _config_path(project_root, app_path, RETENTION_FILENAME)

def load_auth_config(
    project_root: str | Path | None,
    app_path: str | Path | None,
    *,
    required: bool = False,
) -> AuthConfig | None:
    path = auth_config_path(project_root, app_path)
    payload = _load_payload(path, required=required, filename=AUTH_FILENAME)
    if payload is None:
        return None
    _ensure_allowed_keys(payload, {"version", "roles", "authentication"}, path=path, filename=AUTH_FILENAME)
    version = _text(payload.get("version")) or "1.0"
    roles_raw = payload.get("roles")
    roles = _parse_roles(roles_raw, path=path)
    auth_block = payload.get("authentication")
    methods = _parse_methods(auth_block, path=path)
    return AuthConfig(version=version, roles=roles, methods=methods)

def load_security_config(
    project_root: str | Path | None,
    app_path: str | Path | None,
    *,
    required: bool = False,
) -> SecurityConfig | None:
    path = security_config_path(project_root, app_path)
    payload = _load_payload(path, required=required, filename=SECURITY_FILENAME)
    if payload is None:
        return None
    _ensure_allowed_keys(
        payload,
        {"version", "encryption", "resource_limits"},
        path=path,
        filename=SECURITY_FILENAME,
    )
    version = _text(payload.get("version")) or "1.0"
    encryption = payload.get("encryption")
    resource_limits = payload.get("resource_limits")
    if not isinstance(encryption, dict):
        raise Namel3ssError(_invalid_section_message(path, SECURITY_FILENAME, "encryption"))
    if not isinstance(resource_limits, dict):
        raise Namel3ssError(_invalid_section_message(path, SECURITY_FILENAME, "resource_limits"))
    _ensure_allowed_keys(
        encryption,
        {"enabled", "algorithm", "key"},
        path=path,
        filename=SECURITY_FILENAME,
        section="encryption",
    )
    _ensure_allowed_keys(
        resource_limits,
        {"max_memory_mb", "max_cpu_ms"},
        path=path,
        filename=SECURITY_FILENAME,
        section="resource_limits",
    )

    encryption_enabled = _bool_value(
        encryption.get("enabled"),
        default=True,
        field_name="encryption.enabled",
        path=path,
        filename=SECURITY_FILENAME,
    )
    encryption_algorithm = _text(encryption.get("algorithm")) or "aes-256-gcm"
    encryption_key_ref = _text(encryption.get("key"))
    if not encryption_key_ref:
        raise Namel3ssError(_required_field_message(path, SECURITY_FILENAME, "encryption.key", "env:N3_ENCRYPTION_KEY"))
    if not encryption_key_ref.startswith("env:"):
        raise Namel3ssError(_env_ref_message(path, SECURITY_FILENAME, "encryption.key"))

    max_memory_mb = _positive_int(
        resource_limits.get("max_memory_mb"),
        field_name="resource_limits.max_memory_mb",
        default=256,
        path=path,
        filename=SECURITY_FILENAME,
    )
    max_cpu_ms = _positive_int(
        resource_limits.get("max_cpu_ms"),
        field_name="resource_limits.max_cpu_ms",
        default=5000,
        path=path,
        filename=SECURITY_FILENAME,
    )

    return SecurityConfig(
        version=version,
        encryption_enabled=encryption_enabled,
        encryption_algorithm=encryption_algorithm,
        encryption_key_ref=encryption_key_ref,
        max_memory_mb=max_memory_mb,
        max_cpu_ms=max_cpu_ms,
    )

def load_retention_config(
    project_root: str | Path | None,
    app_path: str | Path | None,
    *,
    required: bool = False,
) -> RetentionConfig | None:
    path = retention_config_path(project_root, app_path)
    payload = _load_payload(path, required=required, filename=RETENTION_FILENAME)
    if payload is None:
        return None
    _ensure_allowed_keys(payload, {"version", "records", "audit"}, path=path, filename=RETENTION_FILENAME)
    version = _text(payload.get("version")) or "1.0"
    records_raw = payload.get("records")
    records = _parse_records(records_raw, path=path)
    audit_raw = payload.get("audit")
    if audit_raw is not None and not isinstance(audit_raw, dict):
        raise Namel3ssError(_invalid_section_message(path, RETENTION_FILENAME, "audit"))
    audit_block = dict(audit_raw) if isinstance(audit_raw, dict) else {}
    _ensure_allowed_keys(audit_block, {"enabled", "retention_days"}, path=path, filename=RETENTION_FILENAME, section="audit")
    audit_enabled = _bool_value(
        audit_block.get("enabled"),
        default=True,
        field_name="audit.enabled",
        path=path,
        filename=RETENTION_FILENAME,
    )
    audit_retention_days = _positive_int(
        audit_block.get("retention_days"),
        field_name="audit.retention_days",
        default=30,
        path=path,
        filename=RETENTION_FILENAME,
    )
    return RetentionConfig(
        version=version,
        records=records,
        audit_enabled=audit_enabled,
        audit_retention_days=audit_retention_days,
    )

def _config_path(project_root: str | Path | None, app_path: str | Path | None, filename: str) -> Path | None:
    if project_root is not None:
        return Path(project_root).resolve() / filename
    if app_path is not None:
        return Path(app_path).resolve().parent / filename
    return None

def _load_payload(path: Path | None, *, required: bool, filename: str) -> dict[str, Any] | None:
    if path is None:
        if required:
            raise Namel3ssError(_missing_file_message(Path(filename), filename))
        return None
    if not path.exists():
        if required:
            raise Namel3ssError(_missing_file_message(path, filename))
        return None
    try:
        payload = parse_yaml(path.read_text(encoding="utf-8"))
    except Exception as err:
        raise Namel3ssError(_invalid_yaml_message(path, filename)) from err
    if not isinstance(payload, dict):
        raise Namel3ssError(_invalid_yaml_message(path, filename))
    return dict(payload)

def _parse_roles(value: object, *, path: Path | None) -> dict[str, tuple[str, ...]]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise Namel3ssError(_invalid_section_message(path, AUTH_FILENAME, "roles"))
    roles: dict[str, tuple[str, ...]] = {}
    for role_name in sorted(value.keys(), key=lambda item: str(item)):
        key = _text(role_name)
        if not key:
            continue
        raw = value.get(role_name)
        permissions = _permissions_from_raw(raw, path=path)
        roles[key] = tuple(sorted(permissions))
    return roles


def _permissions_from_raw(value: object, *, path: Path | None) -> list[str]:
    if isinstance(value, dict):
        value = value.get("permissions")
    if value is None:
        return []
    if not isinstance(value, list):
        raise Namel3ssError(_invalid_roles_permissions_message(path))
    permissions: list[str] = []
    for item in value:
        text = _text(item)
        if text and text not in permissions:
            permissions.append(text)
    permissions.sort()
    return permissions


def _parse_methods(value: object, *, path: Path | None) -> dict[str, bool]:
    if value is None:
        return {name: True for name in _ALLOWED_LOGIN_METHODS}
    if not isinstance(value, dict):
        raise Namel3ssError(_invalid_section_message(path, AUTH_FILENAME, "authentication"))
    methods_raw = value.get("methods")
    if methods_raw is None:
        return {name: True for name in _ALLOWED_LOGIN_METHODS}
    if not isinstance(methods_raw, dict):
        raise Namel3ssError(_invalid_section_message(path, AUTH_FILENAME, "authentication.methods"))
    _ensure_allowed_keys(
        methods_raw,
        set(_ALLOWED_LOGIN_METHODS),
        path=path,
        filename=AUTH_FILENAME,
        section="authentication.methods",
    )
    methods: dict[str, bool] = {}
    for name in _ALLOWED_LOGIN_METHODS:
        methods[name] = _bool_value(
            methods_raw.get(name),
            default=True,
            field_name=f"authentication.methods.{name}",
            path=path,
            filename=AUTH_FILENAME,
        )
    return methods


def _parse_records(value: object, *, path: Path | None) -> dict[str, RetentionRecordRule]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise Namel3ssError(_invalid_section_message(path, RETENTION_FILENAME, "records"))
    records: dict[str, RetentionRecordRule] = {}
    for key in sorted(value.keys(), key=lambda item: str(item)):
        name = _text(key)
        if not name:
            continue
        raw = value.get(key)
        if not isinstance(raw, dict):
            raise Namel3ssError(_invalid_section_message(path, RETENTION_FILENAME, f"records.{name}"))
        _ensure_allowed_keys(raw, {"retention_days", "anonymize_fields"}, path=path, filename=RETENTION_FILENAME, section=f"records.{name}")
        retention_days = _positive_int(
            raw.get("retention_days"),
            field_name=f"records.{name}.retention_days",
            default=30,
            path=path,
            filename=RETENTION_FILENAME,
        )
        anonymize_raw = raw.get("anonymize_fields")
        anonymize_fields: list[str] = []
        if anonymize_raw is not None:
            if not isinstance(anonymize_raw, list):
                raise Namel3ssError(_invalid_section_message(path, RETENTION_FILENAME, f"records.{name}.anonymize_fields"))
            for field in anonymize_raw:
                text = _text(field)
                if text and text not in anonymize_fields:
                    anonymize_fields.append(text)
        anonymize_fields.sort()
        records[name] = RetentionRecordRule(retention_days=retention_days, anonymize_fields=tuple(anonymize_fields))
    return records


def _ensure_allowed_keys(
    payload: dict[str, Any],
    allowed: set[str],
    *,
    path: Path | None,
    filename: str,
    section: str | None = None,
) -> None:
    unknown = sorted(key for key in payload.keys() if str(key) not in allowed)
    if not unknown:
        return
    raise Namel3ssError(_unknown_keys_message(path, filename, unknown, section=section))


def _text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _bool_value(value: object, *, default: bool, field_name: str, path: Path | None, filename: str) -> bool:
    if value is None:
        return bool(default)
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    raise Namel3ssError(_invalid_bool_message(path, filename, field_name))


def _positive_int(value: object, *, field_name: str, default: int, path: Path | None, filename: str) -> int:
    if value is None:
        return int(default)
    try:
        parsed = int(str(value).strip())
    except Exception as err:
        raise Namel3ssError(_invalid_int_message(path, filename, field_name)) from err
    if parsed < 1:
        raise Namel3ssError(_invalid_int_message(path, filename, field_name))
    return parsed


def _missing_file_message(path: Path, filename: str) -> str:
    return build_guidance_message(
        what=f"Missing {filename}.",
        why=f"Expected configuration file at {path.as_posix()}.",
        fix=f"Create {filename} with version and required sections.",
        example=f"{filename}: version: \"1.0\"",
    )


def _invalid_yaml_message(path: Path, filename: str) -> str:
    return build_guidance_message(
        what=f"{filename} is invalid.",
        why=f"Could not parse {path.as_posix()} as YAML.",
        fix="Fix YAML syntax and retry.",
        example='version: "1.0"',
    )


def _invalid_section_message(path: Path | None, filename: str, section: str) -> str:
    target = path.as_posix() if path is not None else filename
    return build_guidance_message(
        what=f"{filename} section '{section}' is invalid.",
        why=f"{target} must define '{section}' as a map with expected fields.",
        fix=f"Fix section '{section}' in {filename}.",
        example=f"{section}:",
    )


def _invalid_roles_permissions_message(path: Path | None) -> str:
    target = path.as_posix() if path is not None else AUTH_FILENAME
    return build_guidance_message(
        what="auth.yaml role permissions are invalid.",
        why=f"Role permissions in {target} must be a list of text values.",
        fix="Set permissions as a YAML list.",
        example='roles:\n  admin:\n    permissions:\n      - records.delete',
    )


def _unknown_keys_message(path: Path | None, filename: str, unknown: list[str], *, section: str | None) -> str:
    location = f"{filename}.{section}" if section else filename
    target = path.as_posix() if path is not None else filename
    names = ", ".join(unknown)
    return build_guidance_message(
        what=f"Unknown key in {location}.",
        why=f"{target} contains unsupported keys: {names}.",
        fix="Remove unsupported keys or rename them to documented fields.",
        example='version: "1.0"',
    )


def _required_field_message(path: Path | None, filename: str, field_name: str, example_value: str) -> str:
    target = path.as_posix() if path is not None else filename
    return build_guidance_message(
        what=f"{filename} field '{field_name}' is required.",
        why=f"{target} must define '{field_name}' for deterministic security setup.",
        fix=f"Set '{field_name}' to a valid value.",
        example=f"{field_name}: {example_value}",
    )


def _env_ref_message(path: Path | None, filename: str, field_name: str) -> str:
    target = path.as_posix() if path is not None else filename
    return build_guidance_message(
        what=f"{filename} field '{field_name}' must use env reference.",
        why=f"{target} must not hardcode secrets.",
        fix="Use env:VARIABLE_NAME format.",
        example=f"{field_name}: env:N3_ENCRYPTION_KEY",
    )


def _invalid_bool_message(path: Path | None, filename: str, field_name: str) -> str:
    target = path.as_posix() if path is not None else filename
    return build_guidance_message(
        what=f"{filename} field '{field_name}' must be true or false.",
        why=f"{target} contains a non-boolean value for '{field_name}'.",
        fix="Use true or false.",
        example=f"{field_name}: true",
    )


def _invalid_int_message(path: Path | None, filename: str, field_name: str) -> str:
    target = path.as_posix() if path is not None else filename
    return build_guidance_message(
        what=f"{filename} field '{field_name}' must be a positive integer.",
        why=f"{target} contains an invalid number for '{field_name}'.",
        fix="Use a positive number.",
        example=f"{field_name}: 30",
    )


__all__ = [
    "AUTH_FILENAME",
    "RETENTION_FILENAME",
    "SECURITY_FILENAME",
    "AuthConfig",
    "RetentionConfig",
    "RetentionRecordRule",
    "SecurityConfig",
    "auth_config_path",
    "load_auth_config",
    "load_retention_config",
    "load_security_config",
    "retention_config_path",
    "security_config_path",
]
