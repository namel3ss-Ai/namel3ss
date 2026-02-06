from pathlib import Path
import json

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


def test_manifest_merges_package_metadata_and_dependencies(tmp_path: Path) -> None:
    (tmp_path / "namel3ss.toml").write_text(
        '[package]\nname = "app_pkg"\nversion = "1.0.0"\ncapabilities = ["http", "security_compliance"]\n\n'
        '[dependencies]\ninv = "github:owner/repo@v0.1.0"\n',
        encoding="utf-8",
    )
    (tmp_path / "namel3ss.package.json").write_text(
        json.dumps(
            {
                "name": "app_pkg",
                "version": "1.0.0",
                "capabilities": ["http", "security_compliance"],
                "dependencies": {
                    "shared": {
                        "source": "github:owner/shared@v0.2.0",
                        "version": "^0.2",
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    manifest = load_manifest(tmp_path)
    assert manifest.package_name == "app_pkg"
    assert manifest.package_version == "1.0.0"
    assert manifest.capabilities == ("http", "security_compliance")
    assert set(manifest.dependencies.keys()) == {"inv", "shared"}


def test_manifest_rejects_dependency_conflict_between_toml_and_metadata(tmp_path: Path) -> None:
    (tmp_path / "namel3ss.toml").write_text(
        '[dependencies]\ninv = "github:owner/repo@v0.1.0"\n',
        encoding="utf-8",
    )
    (tmp_path / "namel3ss.package.json").write_text(
        json.dumps(
            {
                "name": "app_pkg",
                "version": "1.0.0",
                "dependencies": {
                    "inv": {
                        "source": "github:owner/repo@v0.2.0",
                        "version": "^0.2",
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(Namel3ssError):
        load_manifest(tmp_path)


def test_manifest_parses_runtime_dependencies(tmp_path: Path) -> None:
    path = tmp_path / "namel3ss.toml"
    path.write_text(
        '[dependencies]\ninv = "github:owner/repo@v0.1.0"\n\n'
        "[runtime.dependencies]\n"
        'python = ["requests==2.31.0", "httpx@0.27.0"]\n'
        'system = ["postgresql-client@13"]\n',
        encoding="utf-8",
    )
    manifest = load_manifest(tmp_path)
    assert manifest.runtime_python_dependencies == ("httpx@0.27.0", "requests==2.31.0")
    assert manifest.runtime_system_dependencies == ("postgresql-client@13",)


def test_manifest_runtime_dependencies_must_be_string_lists(tmp_path: Path) -> None:
    path = tmp_path / "namel3ss.toml"
    path.write_text(
        '[dependencies]\ninv = "github:owner/repo@v0.1.0"\n\n'
        "[runtime.dependencies]\n"
        "python = 123\n",
        encoding="utf-8",
    )
    with pytest.raises(Namel3ssError):
        load_manifest(tmp_path)
