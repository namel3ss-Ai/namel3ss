from __future__ import annotations

import hashlib
import json
import os
import zipfile
from io import BytesIO
from pathlib import Path

from namel3ss.cli.main import main
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


def test_cli_pkg_commands(monkeypatch, tmp_path, capsys):
    app = tmp_path / "app.ai"
    app.write_text('flow "demo":\n  return "ok"\n', encoding="utf-8")
    manifest = tmp_path / "namel3ss.toml"
    manifest.write_text('[dependencies]\ndemo = "github:owner/demo@v0.1.0"\n', encoding="utf-8")

    package_root = tmp_path / "package_src"
    package_root.mkdir()
    (package_root / "capsule.ai").write_text('capsule "demo":\n  exports:\n    flow "run"\n', encoding="utf-8")
    (package_root / "logic.ai").write_text('flow "run":\n  return "ok"\n', encoding="utf-8")
    (package_root / "LICENSE").write_text("MIT", encoding="utf-8")
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
        assert main(["pkg", "plan", "--json"]) == 0
        plan_out = json.loads(capsys.readouterr().out)
        assert plan_out["changes"]

        assert main(["pkg", "install", "--json"]) == 0
        install_out = json.loads(capsys.readouterr().out)
        assert install_out["status"] == "ok"
        assert (tmp_path / "packages" / "demo" / "capsule.ai").exists()

        assert main(["pkg", "tree", "--json"]) == 0
        tree_out = json.loads(capsys.readouterr().out)
        assert "nodes" in tree_out

        assert main(["pkg", "why", "demo", "--json"]) == 0
        why_out = json.loads(capsys.readouterr().out)
        assert why_out["paths"]

        assert main(["pkg", "licenses", "--json"]) == 0
        licenses_out = json.loads(capsys.readouterr().out)
        assert licenses_out["licenses"][0]["name"] == "demo"

        assert main(["pkg", "verify", "--json"]) == 0
        verify_out = json.loads(capsys.readouterr().out)
        assert verify_out["status"] == "ok"
    finally:
        os.chdir(prev)
