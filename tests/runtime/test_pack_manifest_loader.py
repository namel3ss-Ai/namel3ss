from __future__ import annotations

from pathlib import Path

from namel3ss.runtime.packs.pack_manifest import load_pack_contents


def test_pack_contents_reports_missing_manifest(tmp_path: Path) -> None:
    pack_dir = tmp_path / "packs" / "capability" / "missing"
    pack_dir.mkdir(parents=True, exist_ok=True)
    contents = load_pack_contents(pack_dir)
    assert contents.manifest is None
    assert contents.errors


def test_pack_contents_reports_missing_bindings(tmp_path: Path) -> None:
    pack_dir = tmp_path / "packs" / "capability" / "incomplete"
    pack_dir.mkdir(parents=True, exist_ok=True)
    (pack_dir / "pack.yaml").write_text(
        'id: "example.incomplete"\n'
        'name: "Example Pack"\n'
        'version: "stable"\n'
        'description: "Missing tools.yaml."\n'
        'author: "Namel3ss"\n'
        'license: "MIT"\n'
        'tools:\n'
        '  - "compose greeting"\n',
        encoding="utf-8",
    )
    contents = load_pack_contents(pack_dir)
    assert contents.manifest is not None
    assert any("missing tool bindings" in err for err in contents.errors)
