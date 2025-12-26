from __future__ import annotations

import hashlib
import json
import os
import zipfile
from io import BytesIO
from pathlib import Path

from namel3ss.cli.main import main
from namel3ss.pkg.index import INDEX_PATH_ENV
from namel3ss.pkg.sources.github import GitHubFetcher


def _sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _write_checksums(root: Path) -> None:
    files = {}
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.name == "checksums.json":
            continue
        rel = path.relative_to(root).as_posix()
        files[rel] = f"sha256:{_sha256(path)}"
    (root / "checksums.json").write_text(json.dumps({"files": files}, indent=2), encoding="utf-8")


def _zip_bytes(root: Path, prefix: str) -> bytes:
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            rel = path.relative_to(root).as_posix()
            zipf.write(path, f"{prefix}/{rel}")
    return buffer.getvalue()


def test_cli_pkg_search_info_add(monkeypatch, tmp_path, capsys):
    app = tmp_path / "app.ai"
    app.write_text('flow "demo":\n  return "ok"\n', encoding="utf-8")

    index_path = Path("tests/fixtures/pkg_index.json").resolve()
    monkeypatch.setenv(INDEX_PATH_ENV, str(index_path))

    package_root = tmp_path / "package_src"
    package_root.mkdir()
    (package_root / "capsule.ai").write_text('capsule "demo":\n  exports:\n    flow "run"\n', encoding="utf-8")
    (package_root / "logic.ai").write_text('flow "run":\n  return "ok"\n', encoding="utf-8")
    (package_root / "LICENSE").write_text("MIT", encoding="utf-8")
    (package_root / "README.md").write_text("Demo package README.\n", encoding="utf-8")
    metadata = {
        "name": "demo",
        "version": "0.1.0",
        "source": "github:owner/demo@v0.1.0",
        "license_file": "LICENSE",
        "checksums": "checksums.json",
    }
    (package_root / "namel3ss.package.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    _write_checksums(package_root)

    archive = _zip_bytes(package_root, "owner-demo-v0.1.0")
    monkeypatch.setattr(GitHubFetcher, "_download_archive", lambda self, source: archive)

    prev = os.getcwd()
    os.chdir(tmp_path)
    try:
        assert main(["pkg", "search", "demo", "--json"]) == 0
        search_out = json.loads(capsys.readouterr().out)
        assert search_out["count"] == 1

        assert main(["pkg", "info", "demo", "--json"]) == 0
        info_out = json.loads(capsys.readouterr().out)
        assert info_out["name"] == "demo"
        assert "install" in info_out

        assert main(["pkg", "add", "demo", "--json"]) == 0
        add_out = json.loads(capsys.readouterr().out)
        assert add_out["status"] == "ok"
        assert (tmp_path / "namel3ss.toml").exists()

        assert main(["pkg", "validate", str(package_root), "--json"]) == 0
        validate_out = json.loads(capsys.readouterr().out)
        assert validate_out["status"] == "ok"
    finally:
        os.chdir(prev)
