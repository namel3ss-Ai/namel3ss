from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Mapping
from urllib.parse import unquote


PLUGIN_ASSET_CACHE_CONTROL = "public, max-age=31536000, immutable"


def resolve_plugin_asset(program: object, path: str) -> tuple[bytes, str] | None:
    parts = [segment for segment in str(path or "").split("/") if segment]
    if len(parts) < 6:
        return None
    if parts[0] != "api" or parts[1] != "plugins":
        return None
    plugin_name = parts[2]
    if parts[3] != "assets":
        return None
    asset_type = parts[4]
    if asset_type not in {"js", "css"}:
        return None
    relative_path = _normalize_asset_path("/".join(parts[5:]))
    if not relative_path:
        return None
    if not _is_allowed_asset_path(relative_path):
        return None
    schema = _find_plugin_schema(program, plugin_name)
    if schema is None:
        return None
    allowed_assets = _allowed_assets(schema, asset_type)
    if relative_path not in allowed_assets:
        return None
    plugin_root = Path(getattr(schema, "plugin_root", ".")).resolve()
    asset_file = (plugin_root / relative_path).resolve()
    if plugin_root not in asset_file.parents and asset_file != plugin_root:
        return None
    if not asset_file.exists() or not asset_file.is_file():
        return None
    try:
        data = asset_file.read_bytes()
    except OSError:
        return None
    content_type = "application/javascript" if asset_type == "js" else "text/css"
    return data, content_type


def plugin_asset_headers(payload: bytes) -> dict[str, str]:
    etag = plugin_asset_etag(payload)
    return {
        "Cache-Control": PLUGIN_ASSET_CACHE_CONTROL,
        "ETag": etag,
    }


def plugin_asset_etag(payload: bytes) -> str:
    digest = hashlib.sha256(payload).hexdigest()
    return f'"sha256-{digest}"'


def request_etag_matches(headers: Mapping[str, object], etag: str) -> bool:
    expected = _normalize_etag(etag)
    if expected is None:
        return False
    for key, value in headers.items():
        if str(key).lower() != "if-none-match":
            continue
        if not isinstance(value, str):
            return False
        for token in value.split(","):
            candidate = _normalize_etag(token.strip())
            if candidate == "*" or candidate == expected:
                return True
        return False
    return False


def _find_plugin_schema(program: object, plugin_name: str):
    registry = getattr(program, "ui_plugin_registry", None)
    schemas = tuple(getattr(registry, "plugin_schemas", ()) or ())
    for schema in schemas:
        name = str(getattr(schema, "name", "") or "")
        if name == plugin_name:
            return schema
    return None


def _allowed_assets(schema: object, asset_type: str) -> set[str]:
    values = tuple(getattr(schema, "asset_js" if asset_type == "js" else "asset_css", ()) or ())
    allowed: set[str] = set()
    for value in values:
        normalized = _normalize_asset_path(value)
        if normalized:
            allowed.add(normalized)
    return allowed


def _normalize_asset_path(value: object) -> str:
    text = unquote(str(value or "")).replace("\\", "/").strip()
    text = text.lstrip("./").lstrip("/")
    while "//" in text:
        text = text.replace("//", "/")
    return text


def _is_allowed_asset_path(value: str) -> bool:
    path = Path(value)
    for part in path.parts:
        if part in {"..", ""}:
            return False
    return True


def _normalize_etag(value: object) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    if text == "*":
        return "*"
    if text.startswith("W/"):
        text = text[2:].strip()
    return text or None


__all__ = [
    "PLUGIN_ASSET_CACHE_CONTROL",
    "plugin_asset_etag",
    "plugin_asset_headers",
    "request_etag_matches",
    "resolve_plugin_asset",
]
