from __future__ import annotations

import hashlib
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from namel3ss.cli.main import main as cli_main
from namel3ss.runtime.registry.bundle import build_registry_entry_from_bundle


FIXTURES_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "registry" / "bundles"


def test_http_registry_discover_and_install(tmp_path: Path, capsys, monkeypatch) -> None:
    _write_app(tmp_path)
    monkeypatch.chdir(tmp_path)
    bundle_local = FIXTURES_ROOT / "sample.local-0.1.0.n3pack.zip"
    _add_trusted_key(tmp_path, _signature_from_bundle(bundle_local))
    capsys.readouterr()

    bundles_map: dict[str, bytes] = {}
    entries: list[dict[str, object]] = []

    server = HTTPServer(("127.0.0.1", 0), _handler(entries, bundles_map))
    port = server.server_address[1]
    base_url = f"http://127.0.0.1:{port}/registry"

    entries.extend(_registry_entries(tmp_path, base_url))
    for bundle_path in FIXTURES_ROOT.glob("*.n3pack.zip"):
        digest = _bundle_digest(bundle_path)
        bundles_map[digest] = bundle_path.read_bytes()

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        _write_registry_config(tmp_path, base_url)
        assert cli_main(["discover", "provide", "--json"]) == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["count"] >= 1
        assert cli_main(["packs", "add", "sample.local@0.1.0", "--from", "team", "--json"]) == 0
        capsys.readouterr()
        assert (tmp_path / ".namel3ss" / "packs" / "sample.local" / "pack.yaml").exists()
    finally:
        server.shutdown()
        thread.join(timeout=1)


def _registry_entries(app_root: Path, base_url: str) -> list[dict[str, object]]:
    entries = []
    for bundle_path in FIXTURES_ROOT.glob("*.n3pack.zip"):
        result = build_registry_entry_from_bundle(
            bundle_path,
            app_root=app_root,
            source_kind="registry_url",
            source_uri=base_url,
        )
        entries.append(result.entry.to_dict())
    return entries


def _bundle_digest(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return f"sha256:{digest.hexdigest()}"


def _handler(entries: list[dict[str, object]], bundles: dict[str, bytes]):
    class RegistryHandler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args) -> None:  # pragma: no cover - silence
            return

        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/registry/search":
                self.send_error(404)
                return
            payload = json.dumps({"entries": entries}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self) -> None:  # noqa: N802
            if not self.path.startswith("/registry/bundle/"):
                self.send_error(404)
                return
            digest = self.path.split("/registry/bundle/", 1)[-1]
            if digest not in bundles:
                self.send_error(404)
                return
            payload = bundles[digest]
            self.send_response(200)
            self.send_header("Content-Type", "application/zip")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    return RegistryHandler


def _signature_from_bundle(path: Path) -> str:
    import zipfile

    with zipfile.ZipFile(path, "r") as archive:
        data = archive.read("signature.txt")
    return data.decode("utf-8").strip()


def _add_trusted_key(app_root: Path, digest: str) -> None:
    key_file = app_root / "trusted.key"
    key_file.write_text(digest, encoding="utf-8")
    assert cli_main(["packs", "keys", "add", "--id", "test.key", "--public-key", str(key_file), "--json"]) == 0


def _write_registry_config(app_root: Path, base_url: str) -> None:
    config = (
        "[registries]\n"
        "sources = [\n"
        f'  {{ id = "team", kind = "http", url = "{base_url}" }}\n'
        "]\n"
        'default = ["team"]\n'
    )
    (app_root / "namel3ss.toml").write_text(config, encoding="utf-8")


def _write_app(tmp_path: Path) -> None:
    (tmp_path / "app.ai").write_text('flow \"demo\":\n  return \"ok\"\n', encoding="utf-8")
