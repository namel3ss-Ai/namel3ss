from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from io import BytesIO
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message

_CACHE_FILE = ".namel3ss/cache/remote_registry_cache.json"
_DEFAULT_TIMEOUT_SECONDS = 5


def remote_registry_url(
    *,
    project_root: str | Path,
    override: str | None = None,
) -> str | None:
    if isinstance(override, str) and override.strip().lower().startswith(("http://", "https://")):
        return override.strip().rstrip("/")
    env_url = os.getenv("N3_REMOTE_REGISTRY_URL")
    if isinstance(env_url, str) and env_url.strip().lower().startswith(("http://", "https://")):
        return env_url.strip().rstrip("/")
    return None


def list_remote_plugins(
    *,
    project_root: str | Path,
    base_url: str,
    keyword: str | None = None,
) -> list[dict[str, object]]:
    if keyword:
        query = urllib.parse.urlencode({"q": keyword})
        path = f"/plugins/search?{query}"
    else:
        path = "/plugins"
    payload = _request_json_with_cache(project_root=project_root, base_url=base_url, path=path)
    entries = _payload_entries(payload)
    return sorted(entries, key=_entry_sort_key)


def remote_plugin_info(
    *,
    project_root: str | Path,
    base_url: str,
    name: str,
    version: str | None = None,
) -> dict[str, object]:
    if version:
        path = f"/plugins/{urllib.parse.quote(name)}/{urllib.parse.quote(version)}"
    else:
        path = f"/plugins/{urllib.parse.quote(name)}"
    payload = _request_json_with_cache(project_root=project_root, base_url=base_url, path=path)
    plugin = payload.get("plugin") if isinstance(payload, dict) else None
    if not isinstance(plugin, dict):
        raise Namel3ssError(_remote_payload_error("plugin info payload is invalid"))
    return dict(plugin)


def download_remote_plugin(
    *,
    project_root: str | Path,
    download_url: str,
    destination: Path,
) -> None:
    request = urllib.request.Request(url=download_url, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=_DEFAULT_TIMEOUT_SECONDS) as response:  # noqa: S310
            archive = response.read()
    except urllib.error.HTTPError as err:
        details = err.read().decode("utf-8", errors="replace")
        raise Namel3ssError(_remote_download_error(download_url, f"{err.code} {details or err.reason}")) from err
    except urllib.error.URLError as err:
        raise Namel3ssError(_remote_download_error(download_url, str(err.reason))) from err
    destination.mkdir(parents=True, exist_ok=False)
    try:
        with zipfile.ZipFile(BytesIO(archive)) as zf:
            names = sorted([name for name in zf.namelist() if not name.endswith("/")])
            for name in names:
                target = destination / Path(name)
                target.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(name, "r") as source:
                    target.write_bytes(source.read())
    except zipfile.BadZipFile as err:
        raise Namel3ssError(_remote_download_error(download_url, "download payload is not a valid zip archive")) from err


def make_download_url(base_url: str, *, name: str, version: str) -> str:
    return (
        f"{base_url.rstrip('/')}/plugins/{urllib.parse.quote(name)}/"
        f"{urllib.parse.quote(version)}/download"
    )


def _request_json_with_cache(
    *,
    project_root: str | Path,
    base_url: str,
    path: str,
) -> object:
    normalized_base = base_url.rstrip("/")
    url = f"{normalized_base}{path}"
    cache = _load_cache(project_root)
    cache_key = _cache_key(url)
    request = urllib.request.Request(url=url, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=_DEFAULT_TIMEOUT_SECONDS) as response:  # noqa: S310
            body = response.read().decode("utf-8")
        payload = json.loads(body or "{}")
        cache[cache_key] = payload
        _save_cache(project_root, cache)
        return payload
    except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError):
        if cache_key in cache:
            return cache[cache_key]
        raise


def _load_cache(project_root: str | Path) -> dict[str, object]:
    path = Path(project_root).resolve() / _CACHE_FILE
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(payload, dict):
        return {}
    normalized: dict[str, object] = {}
    for key in sorted(payload.keys()):
        normalized[str(key)] = payload[key]
    return normalized


def _save_cache(project_root: str | Path, cache: dict[str, object]) -> None:
    path = Path(project_root).resolve() / _CACHE_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cache, indent=2, sort_keys=True), encoding="utf-8")


def _cache_key(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def _payload_entries(payload: object) -> list[dict[str, object]]:
    if not isinstance(payload, dict):
        raise Namel3ssError(_remote_payload_error("registry payload is not an object"))
    entries = payload.get("plugins")
    if not isinstance(entries, list):
        raise Namel3ssError(_remote_payload_error("registry payload does not include plugins list"))
    normalized: list[dict[str, object]] = []
    for item in entries:
        if isinstance(item, dict):
            normalized.append(dict(item))
    return normalized


def _entry_sort_key(item: dict[str, object]) -> tuple[str, str]:
    name = str(item.get("name") or "")
    version = str(item.get("version") or "")
    return (name, version)


def _remote_payload_error(detail: str) -> str:
    return build_guidance_message(
        what="Remote registry payload is invalid.",
        why=detail,
        fix="Retry, then verify the remote registry server implementation.",
        example="n3 plugin search charts --json",
    )


def _remote_download_error(url: str, detail: str) -> str:
    return build_guidance_message(
        what=f"Failed to download remote extension package from {url}.",
        why=detail,
        fix="Verify network connectivity and registry package integrity.",
        example="n3 plugin install charts@1.0.0 --yes",
    )


__all__ = [
    "download_remote_plugin",
    "list_remote_plugins",
    "make_download_url",
    "remote_plugin_info",
    "remote_registry_url",
]
