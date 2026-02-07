from __future__ import annotations

import json
import urllib.parse
import zipfile
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from pathlib import Path

from namel3ss.plugin.trust import compute_tree_hash
from namel3ss.ui.plugins.loader import PLUGIN_MANIFEST_FILES
from namel3ss.ui.plugins.schema import parse_plugin_manifest
from namel3ss.utils.simple_yaml import parse_yaml
from namel3ss.versioning.semver import version_sort_key


@dataclass(frozen=True)
class RemoteRegistryServerConfig:
    registry_root: Path


def create_remote_registry_server(host: str, port: int, *, registry_root: str | Path) -> ThreadingHTTPServer:
    config = RemoteRegistryServerConfig(registry_root=Path(registry_root).resolve())
    server = ThreadingHTTPServer((host, int(port)), RemoteRegistryRequestHandler)
    server.registry_config = config  # type: ignore[attr-defined]
    return server


class RemoteRegistryRequestHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path or "/")
        path = parsed.path.rstrip("/") or "/"
        query = urllib.parse.parse_qs(parsed.query or "")
        if path == "/plugins":
            entries = _load_registry_entries(self._registry_root())
            self._respond_json({"ok": True, "plugins": entries})
            return
        if path == "/plugins/search":
            entries = _load_registry_entries(self._registry_root())
            keyword = str((query.get("q") or [""])[0] or "").strip().lower()
            if keyword:
                entries = [
                    entry
                    for entry in entries
                    if keyword in f"{entry.get('name','')} {entry.get('author','')} {entry.get('description','')}".lower()
                ]
            self._respond_json({"ok": True, "plugins": entries})
            return
        parts = [item for item in path.split("/") if item]
        if len(parts) == 2 and parts[0] == "plugins":
            name = urllib.parse.unquote(parts[1])
            entries = [entry for entry in _load_registry_entries(self._registry_root()) if entry.get("name") == name]
            if not entries:
                self._respond_json({"ok": False, "error": f"plugin '{name}' not found"}, status=404)
                return
            versions = sorted({str(entry.get("version") or "") for entry in entries}, key=version_sort_key)
            latest_version = versions[-1]
            latest = next(entry for entry in entries if entry.get("version") == latest_version)
            self._respond_json({"ok": True, "plugin": latest, "versions": versions})
            return
        if len(parts) == 3 and parts[0] == "plugins":
            name = urllib.parse.unquote(parts[1])
            version = urllib.parse.unquote(parts[2])
            entry = _find_entry(self._registry_root(), name=name, version=version)
            if entry is None:
                self._respond_json({"ok": False, "error": f"plugin '{name}@{version}' not found"}, status=404)
                return
            self._respond_json({"ok": True, "plugin": entry})
            return
        if len(parts) == 4 and parts[0] == "plugins" and parts[3] == "download":
            name = urllib.parse.unquote(parts[1])
            version = urllib.parse.unquote(parts[2])
            source_dir = self._registry_root() / name / version
            if not source_dir.exists() or not source_dir.is_dir():
                self._respond_json({"ok": False, "error": f"plugin '{name}@{version}' not found"}, status=404)
                return
            archive = _zip_plugin_dir(source_dir)
            self.send_response(200)
            self.send_header("Content-Type", "application/zip")
            self.send_header("Content-Length", str(len(archive)))
            self.end_headers()
            self.wfile.write(archive)
            return
        self._respond_json({"ok": False, "error": "not found"}, status=404)

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return

    def _registry_root(self) -> Path:
        config = getattr(self.server, "registry_config", None)  # type: ignore[attr-defined]
        root = getattr(config, "registry_root", None)
        return Path(root).resolve()

    def _respond_json(self, payload: dict[str, object], *, status: int = 200) -> None:
        body = json.dumps(payload, sort_keys=True).encode("utf-8")
        self.send_response(int(status))
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _find_entry(registry_root: Path, *, name: str, version: str) -> dict[str, object] | None:
    for entry in _load_registry_entries(registry_root):
        if entry.get("name") == name and entry.get("version") == version:
            return entry
    return None


def _load_registry_entries(registry_root: Path) -> list[dict[str, object]]:
    if not registry_root.exists() or not registry_root.is_dir():
        return []
    entries: list[dict[str, object]] = []
    for name_dir in sorted([item for item in registry_root.iterdir() if item.is_dir()], key=lambda p: p.name):
        versions = sorted([item for item in name_dir.iterdir() if item.is_dir()], key=lambda p: version_sort_key(p.name))
        for version_dir in versions:
            manifest = _find_manifest(version_dir)
            if manifest is None:
                continue
            payload = _read_manifest_payload(manifest)
            schema = parse_plugin_manifest(payload, source_path=manifest, plugin_root=version_dir)
            version = str(schema.version or version_dir.name)
            entries.append(
                {
                    "name": schema.name,
                    "version": version,
                    "author": str(schema.author or "unknown"),
                    "description": str(schema.description or ""),
                    "permissions": list(schema.permissions),
                    "hooks": {key: value for key, value in schema.hooks},
                    "min_api_version": int(schema.min_api_version),
                    "signature": schema.signature,
                    "tags": list(schema.tags),
                    "rating": schema.rating,
                    "hash": compute_tree_hash(version_dir),
                    "download_url": f"/plugins/{urllib.parse.quote(schema.name)}/{urllib.parse.quote(version)}/download",
                }
            )
    return sorted(entries, key=lambda item: (str(item.get("name") or ""), version_sort_key(str(item.get("version") or "0.0.0"))))


def _find_manifest(plugin_root: Path) -> Path | None:
    for filename in PLUGIN_MANIFEST_FILES:
        path = plugin_root / filename
        if path.exists() and path.is_file():
            return path.resolve()
    return None


def _read_manifest_payload(path: Path) -> object:
    raw = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        return json.loads(raw)
    return parse_yaml(raw)


def _zip_plugin_dir(source_dir: Path) -> bytes:
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file_path in sorted([item for item in source_dir.rglob("*") if item.is_file()], key=lambda p: p.as_posix()):
            rel = file_path.relative_to(source_dir).as_posix()
            info = zipfile.ZipInfo(filename=rel)
            info.date_time = (1980, 1, 1, 0, 0, 0)
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, file_path.read_bytes())
    return buffer.getvalue()


__all__ = ["RemoteRegistryServerConfig", "create_remote_registry_server"]
