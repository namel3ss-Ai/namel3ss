from __future__ import annotations

import hashlib
import re

from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.app_loader import LoadedAppArchive
from namel3ss.runtime.app_permissions_engine import KNOWN_APP_PERMISSIONS
from namel3ss.version import get_version


SUPPORTED_ARCHIVE_FORMAT = "n3a.v1"
SUPPORTED_MODES = ("production", "studio")


def validate_loaded_archive(archive: LoadedAppArchive, *, mode: str = "production") -> None:
    if mode not in SUPPORTED_MODES:
        raise Namel3ssError("Run mode must be production or studio.")

    descriptor = archive.descriptor
    archive_meta = descriptor.get("archive")
    if not isinstance(archive_meta, dict):
        raise Namel3ssError("This file is not a namel3ss app.")
    archive_format = archive_meta.get("format")
    if archive_format != SUPPORTED_ARCHIVE_FORMAT:
        raise Namel3ssError("This file is not a namel3ss app.")

    _validate_version_compatibility(descriptor)
    if "app_packaging" not in _capabilities(descriptor):
        raise Namel3ssError("This file is not a namel3ss app.")
    _validate_permissions(archive.permissions)
    _validate_checksums(archive)


def build_inspection_payload(archive: LoadedAppArchive) -> dict[str, object]:
    descriptor = archive.descriptor
    app_meta = descriptor.get("app") if isinstance(descriptor.get("app"), dict) else {}
    return {
        "app": app_meta.get("name"),
        "permissions": archive.permissions,
        "pages": _pages(descriptor),
        "ui_state": archive.ui_state_schema,
        "capabilities": _capabilities(descriptor),
        "checksum": archive.checksum,
        "namel3ss_version": descriptor.get("namel3ss_version"),
    }


def _validate_version_compatibility(descriptor: dict[str, object]) -> None:
    built = str(descriptor.get("namel3ss_version", "") or "")
    runtime = get_version()
    if _is_newer_version(built, runtime):
        raise Namel3ssError("This app was built with a newer version of namel3ss.")

    spec_version = descriptor.get("language_spec_version")
    if not isinstance(spec_version, str) or not spec_version.strip():
        raise Namel3ssError("This file is not a namel3ss app.")


def _validate_permissions(permissions: dict[str, bool]) -> None:
    for key in KNOWN_APP_PERMISSIONS:
        if key not in permissions:
            raise Namel3ssError("This app asks for permissions it does not declare.")
    for key in permissions.keys():
        if key not in KNOWN_APP_PERMISSIONS:
            raise Namel3ssError("This app asks for permissions it does not declare.")


def _validate_checksums(archive: LoadedAppArchive) -> None:
    checksums = archive.descriptor.get("checksums")
    if not isinstance(checksums, dict):
        raise Namel3ssError("This file is not a namel3ss app.")
    files_map = checksums.get("files")
    content_checksum = checksums.get("content")
    if not isinstance(files_map, dict) or not isinstance(content_checksum, str):
        raise Namel3ssError("This file is not a namel3ss app.")

    normalized_file_map: dict[str, str] = {}
    for name, expected in sorted(files_map.items(), key=lambda item: str(item[0])):
        if not isinstance(name, str) or not isinstance(expected, str):
            raise Namel3ssError("This file is not a namel3ss app.")
        payload = archive.files.get(name)
        if payload is None:
            raise Namel3ssError("This file is not a namel3ss app.")
        actual = hashlib.sha256(payload).hexdigest()
        if actual != expected:
            raise Namel3ssError("This file is not a namel3ss app.")
        normalized_file_map[name] = actual

    actual_content_checksum = hashlib.sha256(
        canonical_json_dumps(normalized_file_map, pretty=True, drop_run_keys=False).encode("utf-8")
    ).hexdigest()
    if actual_content_checksum != content_checksum:
        raise Namel3ssError("This file is not a namel3ss app.")


def _pages(descriptor: dict[str, object]) -> list[str]:
    pages = descriptor.get("pages")
    if not isinstance(pages, list):
        return []
    return [item for item in pages if isinstance(item, str)]


def _capabilities(descriptor: dict[str, object]) -> list[str]:
    capabilities = descriptor.get("capabilities")
    if not isinstance(capabilities, list):
        return []
    return [item for item in capabilities if isinstance(item, str)]


def _is_newer_version(built: str, runtime: str) -> bool:
    built_parts = _version_tuple(built)
    runtime_parts = _version_tuple(runtime)
    if not built_parts or not runtime_parts:
        return False
    max_len = max(len(built_parts), len(runtime_parts))
    built_pad = built_parts + (0,) * (max_len - len(built_parts))
    runtime_pad = runtime_parts + (0,) * (max_len - len(runtime_parts))
    return built_pad > runtime_pad


def _version_tuple(value: str) -> tuple[int, ...]:
    text = str(value or "").strip()
    if not text:
        return ()
    numeric = re.split(r"[^0-9]+", text)
    parts = [int(piece) for piece in numeric if piece != ""]
    return tuple(parts)


__all__ = ["SUPPORTED_ARCHIVE_FORMAT", "SUPPORTED_MODES", "build_inspection_payload", "validate_loaded_archive"]
