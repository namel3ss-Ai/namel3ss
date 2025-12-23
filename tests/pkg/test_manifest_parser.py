from pathlib import Path

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.pkg.manifest import load_manifest, write_manifest


def test_manifest_parses_string_dependency(tmp_path: Path) -> None:
    path = tmp_path / "namel3ss.toml"
    path.write_text('[dependencies]\ninventory = "github:owner/repo@v0.1.0"\n', encoding="utf-8")
    manifest = load_manifest(tmp_path)
    dep = manifest.dependencies["inventory"]
    assert dep.source.owner == "owner"
    assert dep.source.repo == "repo"
    assert dep.source.ref == "v0.1.0"
    assert dep.constraint is not None


def test_manifest_parses_inline_dependency(tmp_path: Path) -> None:
    path = tmp_path / "namel3ss.toml"
    path.write_text(
        '[dependencies]\n'
        'shared = { source = "github:owner/shared@v0.1.2", version = "^0.1" }\n',
        encoding="utf-8",
    )
    manifest = load_manifest(tmp_path)
    dep = manifest.dependencies["shared"]
    assert dep.constraint is not None
    assert dep.constraint.kind == "caret"
    assert dep.constraint_raw == "^0.1"


def test_manifest_invalid_value(tmp_path: Path) -> None:
    path = tmp_path / "namel3ss.toml"
    path.write_text("[dependencies]\ninv = 123\n", encoding="utf-8")
    with pytest.raises(Namel3ssError):
        load_manifest(tmp_path)


def test_manifest_write_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "namel3ss.toml"
    path.write_text('[dependencies]\ninv = "github:owner/repo@v0.1.0"\n', encoding="utf-8")
    manifest = load_manifest(tmp_path)
    write_manifest(tmp_path, manifest)
    written = path.read_text(encoding="utf-8")
    assert "[dependencies]" in written
    assert 'inv = "github:owner/repo@v0.1.0"' in written
