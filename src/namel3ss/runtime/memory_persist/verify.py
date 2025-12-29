from __future__ import annotations

import hashlib
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.memory_persist.format import MEMORY_STORE_VERSION

REQUIRED_KEYS = {
    "version",
    "project_id",
    "clock",
    "ids",
    "phases",
    "ledger",
    "items",
    "agreements",
    "handoffs",
    "budgets",
    "cache",
    "cache_versions",
    "rules",
    "trust",
}


def verify_checksum(snapshot_path: Path, checksum_path: Path) -> None:
    if not checksum_path.exists():
        raise Namel3ssError("Checksum file is missing.")
    expected = checksum_path.read_text(encoding="utf-8").strip()
    if not expected:
        raise Namel3ssError("Checksum file is empty.")
    digest = _sha256(snapshot_path)
    if digest != expected:
        raise Namel3ssError("Checksum did not match.")


def verify_snapshot_payload(payload: dict) -> None:
    if not isinstance(payload, dict):
        raise Namel3ssError("Snapshot payload must be a mapping.")
    missing = [key for key in sorted(REQUIRED_KEYS) if key not in payload]
    if missing:
        raise Namel3ssError(f"Snapshot is missing sections: {', '.join(missing)}.")
    unknown = [key for key in sorted(payload.keys()) if key not in REQUIRED_KEYS]
    if unknown:
        raise Namel3ssError(f"Snapshot has unknown sections: {', '.join(unknown)}.")
    if payload.get("version") != MEMORY_STORE_VERSION:
        raise Namel3ssError("Snapshot version does not match.")
    _require_mapping(payload.get("clock"), "clock")
    _require_mapping(payload.get("ids"), "ids")
    _require_mapping(payload.get("phases"), "phases")
    _require_mapping(payload.get("ledger"), "ledger")
    items = _require_mapping(payload.get("items"), "items")
    _require_list(items.get("stores"), "items.stores")
    _require_mapping(payload.get("agreements"), "agreements")
    _require_mapping(payload.get("handoffs"), "handoffs")
    _require_list(payload.get("budgets"), "budgets")
    _require_mapping(payload.get("cache"), "cache")
    _require_list(payload.get("cache_versions"), "cache_versions")
    _require_mapping(payload.get("rules"), "rules")
    trust = payload.get("trust")
    if trust is not None:
        _require_mapping(trust, "trust")


def _require_mapping(value: object, name: str) -> dict:
    if not isinstance(value, dict):
        raise Namel3ssError(f"Snapshot section {name} must be a mapping.")
    return value


def _require_list(value: object, name: str) -> list:
    if not isinstance(value, list):
        raise Namel3ssError(f"Snapshot section {name} must be a list.")
    return value


def _sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


__all__ = ["verify_checksum", "verify_snapshot_payload"]
