from __future__ import annotations

from pathlib import Path

from namel3ss.cli.main import main as cli_main


def test_pack_add_offline_blocks_remote_registry(tmp_path: Path, capsys, monkeypatch) -> None:
    _write_app(tmp_path)
    _write_registry_config(tmp_path)
    monkeypatch.chdir(tmp_path)
    rc = cli_main(["packs", "add", "sample.local", "--registry", "team", "--offline"])
    assert rc == 1
    captured = capsys.readouterr()
    text = (captured.out + captured.err).lower()
    assert "offline" in text


def _write_registry_config(app_root: Path) -> None:
    config = (
        "[registries]\n"
        "sources = [\n"
        '  { id = "team", kind = "http", url = "http://example.test/registry" }\n'
        "]\n"
        'default = ["team"]\n'
    )
    (app_root / "namel3ss.toml").write_text(config, encoding="utf-8")


def _write_app(tmp_path: Path) -> None:
    (tmp_path / "app.ai").write_text('flow "demo":\n  return "ok"\n', encoding="utf-8")
