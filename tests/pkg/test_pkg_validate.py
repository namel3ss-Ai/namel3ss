from __future__ import annotations

import hashlib
import json
from pathlib import Path

from namel3ss.pkg.validate import validate_package


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


def _make_package(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "capsule.ai").write_text('capsule "demo":\n  exports:\n    flow "run"\n', encoding="utf-8")
    (root / "logic.ai").write_text('spec is "1.0"\n\nflow "run":\n  return "ok"\n', encoding="utf-8")
    (root / "LICENSE").write_text("MIT", encoding="utf-8")
    (root / "README.md").write_text("Demo package README.\n", encoding="utf-8")
    metadata = {
        "name": "demo",
        "version": "0.1.0",
        "source": "github:owner/demo@v0.1.0",
        "license_file": "LICENSE",
        "checksums": "checksums.json",
    }
    (root / "namel3ss.package.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    _write_checksums(root)


def test_pkg_validate_ok(tmp_path: Path) -> None:
    package_root = tmp_path / "pkg"
    _make_package(package_root)
    report = validate_package(str(package_root), strict=False)
    assert report.status == "ok"


def test_pkg_validate_missing_readme(tmp_path: Path) -> None:
    package_root = tmp_path / "pkg"
    _make_package(package_root)
    (package_root / "README.md").unlink()
    _write_checksums(package_root)
    report = validate_package(str(package_root), strict=False)
    assert report.status == "fail"
    messages = [issue.message for issue in report.issues]
    assert any("README" in msg for msg in messages)
