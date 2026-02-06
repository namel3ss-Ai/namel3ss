from __future__ import annotations

from pathlib import Path

from namel3ss.cli.main import main
from namel3ss.plugin.scaffold import render_plugin_files
from namel3ss.utils.slugify import slugify_text


def _assert_scaffold(tmp_path: Path, lang: str, name: str) -> None:
    code = main(["plugin", "new", lang, name])
    assert code == 0
    slug = slugify_text(name)
    plugin_dir = tmp_path / slug
    assert plugin_dir.exists()
    expected = render_plugin_files(lang, name)
    for rel_path, content in expected.items():
        file_path = plugin_dir / rel_path
        assert file_path.exists()
        assert file_path.read_text(encoding="utf-8") == content


def test_plugin_scaffold_node(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _assert_scaffold(tmp_path, "node", "demo_plugin")


def test_plugin_scaffold_go(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _assert_scaffold(tmp_path, "go", "demo_plugin_go")


def test_plugin_scaffold_rust(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _assert_scaffold(tmp_path, "rust", "demo_plugin_rust")
