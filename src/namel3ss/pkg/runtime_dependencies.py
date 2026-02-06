from __future__ import annotations

import hashlib
import re
from typing import Iterable

from namel3ss.pkg.types import Manifest, RuntimeLockEntry


_VERSION_OPERATORS = ("==", ">=", "<=", "~=", "!=", ">", "<")
_NAME_SPLIT_PATTERN = re.compile(r"[<>=!~\s]")


def normalize_python_spec(spec: str) -> str:
    text = str(spec or "").strip()
    if not text:
        return ""
    if any(op in text for op in _VERSION_OPERATORS):
        return text
    if " @ " in text:
        return text
    if "@" in text:
        name, version = text.rsplit("@", 1)
        name = name.strip()
        version = version.strip()
        if name and version:
            return f"{name}=={version}"
    return text


def normalize_system_spec(spec: str) -> str:
    return str(spec or "").strip()


def build_runtime_lock_entries(
    manifest: Manifest,
    *,
    freeze_lines: Iterable[str] | None = None,
    python_artifact_checksums: dict[str, str] | None = None,
    system_artifact_checksums: dict[str, str] | None = None,
) -> tuple[list[RuntimeLockEntry], list[RuntimeLockEntry]]:
    resolved_versions = _freeze_version_map(freeze_lines or ())
    normalized_python_artifacts = _normalize_checksum_map(python_artifact_checksums)
    normalized_system_artifacts = _normalize_checksum_map(system_artifact_checksums)

    python_entries: list[RuntimeLockEntry] = []
    for raw_spec in sorted(set(manifest.runtime_python_dependencies)):
        normalized_spec = normalize_python_spec(raw_spec)
        if not normalized_spec:
            continue
        name = _python_name_from_spec(normalized_spec)
        version = resolved_versions.get(_normalize_name(name)) or _python_version_from_spec(normalized_spec)
        version = version or "*"
        checksum = _resolve_runtime_checksum(
            name=name,
            version=version,
            source="pypi",
            artifact_checksums=normalized_python_artifacts,
        )
        python_entries.append(
            RuntimeLockEntry(
                name=name,
                version=version,
                checksum=checksum,
                source="pypi",
                dependencies={},
                license=None,
                trust_tier="community",
            )
        )

    system_entries: list[RuntimeLockEntry] = []
    for raw_spec in sorted(set(manifest.runtime_system_dependencies)):
        normalized_spec = normalize_system_spec(raw_spec)
        if not normalized_spec:
            continue
        name, version = _system_name_version(normalized_spec)
        checksum = _resolve_runtime_checksum(
            name=name,
            version=version,
            source="system",
            artifact_checksums=normalized_system_artifacts,
        )
        system_entries.append(
            RuntimeLockEntry(
                name=name,
                version=version,
                checksum=checksum,
                source="system",
                dependencies={},
                license=None,
                trust_tier="informational",
            )
        )

    python_entries.sort(key=lambda entry: entry.name)
    system_entries.sort(key=lambda entry: entry.name)
    return python_entries, system_entries


def verify_runtime_lock_entry(entry: RuntimeLockEntry) -> bool:
    return verify_runtime_lock_entry_with_artifacts(entry)


def verify_runtime_lock_entry_with_artifacts(
    entry: RuntimeLockEntry,
    *,
    python_artifact_checksums: dict[str, str] | None = None,
    system_artifact_checksums: dict[str, str] | None = None,
) -> bool:
    checksum = str(entry.checksum or "")
    source = str(entry.source or "")
    if checksum.startswith("artifact:"):
        normalized_name = _normalize_name(entry.name)
        artifact_value = None
        if source == "pypi":
            artifact_value = _normalize_checksum_map(python_artifact_checksums).get(normalized_name)
        elif source == "system":
            artifact_value = _normalize_checksum_map(system_artifact_checksums).get(normalized_name)
        if not artifact_value:
            return False
        return checksum == f"artifact:{artifact_value}"
    if checksum.startswith("spec:"):
        expected = _runtime_checksum(name=entry.name, version=entry.version, source=source)
        return checksum == f"spec:{expected}"
    expected_legacy = _runtime_checksum(name=entry.name, version=entry.version, source=source)
    return checksum == expected_legacy


def _freeze_version_map(lines: Iterable[str]) -> dict[str, str]:
    versions: dict[str, str] = {}
    for raw_line in lines:
        line = str(raw_line or "").strip()
        if not line or line.startswith("#"):
            continue
        if "==" not in line:
            continue
        name, version = line.split("==", 1)
        name = _normalize_name(name)
        version = version.strip()
        if name and version:
            versions[name] = version
    return versions


def _python_name_from_spec(spec: str) -> str:
    if " @ " in spec:
        return spec.split(" @ ", 1)[0].strip()
    for operator in _VERSION_OPERATORS:
        if operator in spec:
            return spec.split(operator, 1)[0].strip()
    if "@" in spec:
        return spec.rsplit("@", 1)[0].strip()
    token = _NAME_SPLIT_PATTERN.split(spec, maxsplit=1)[0]
    return token.strip() or spec.strip()


def _python_version_from_spec(spec: str) -> str:
    if " @ " in spec:
        return spec.split(" @ ", 1)[1].strip() or "*"
    for operator in _VERSION_OPERATORS:
        if operator in spec:
            return spec.split(operator, 1)[1].strip() or "*"
    if "@" in spec:
        return spec.rsplit("@", 1)[1].strip() or "*"
    return "*"


def _system_name_version(spec: str) -> tuple[str, str]:
    if "@" in spec:
        name, version = spec.rsplit("@", 1)
        return name.strip(), version.strip() or "*"
    return spec.strip(), "*"


def _runtime_checksum(*, name: str, version: str, source: str) -> str:
    text = f"{name}|{version}|{source}"
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _resolve_runtime_checksum(
    *,
    name: str,
    version: str,
    source: str,
    artifact_checksums: dict[str, str],
) -> str:
    artifact = artifact_checksums.get(_normalize_name(name))
    if artifact:
        return f"artifact:{artifact}"
    return f"spec:{_runtime_checksum(name=name, version=version, source=source)}"


def _normalize_checksum_map(values: dict[str, str] | None) -> dict[str, str]:
    if not isinstance(values, dict):
        return {}
    output: dict[str, str] = {}
    for key, value in values.items():
        name = _normalize_name(str(key))
        checksum = str(value or "").strip().lower()
        if name and checksum:
            output[name] = checksum
    return output


def _normalize_name(value: str) -> str:
    return str(value or "").strip().lower().replace("_", "-")


__all__ = [
    "build_runtime_lock_entries",
    "normalize_python_spec",
    "normalize_system_spec",
    "verify_runtime_lock_entry",
    "verify_runtime_lock_entry_with_artifacts",
]
