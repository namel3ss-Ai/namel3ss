from __future__ import annotations

from pathlib import Path


REGISTRY_DIR = ".namel3ss/registry"
REGISTRY_INDEX = "index.jsonl"
REGISTRY_COMPACT = "index_compact.json"
REGISTRY_CACHE = "cache"


def registry_root(app_root: Path) -> Path:
    return app_root / REGISTRY_DIR


def registry_index_path(app_root: Path) -> Path:
    return registry_root(app_root) / REGISTRY_INDEX


def registry_compact_path(app_root: Path) -> Path:
    return registry_root(app_root) / REGISTRY_COMPACT


def registry_cache_path(app_root: Path) -> Path:
    return registry_root(app_root) / REGISTRY_CACHE


__all__ = [
    "REGISTRY_CACHE",
    "REGISTRY_COMPACT",
    "REGISTRY_DIR",
    "REGISTRY_INDEX",
    "registry_cache_path",
    "registry_compact_path",
    "registry_index_path",
    "registry_root",
]
