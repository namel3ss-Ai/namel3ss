from __future__ import annotations

import json
from pathlib import Path

from namel3ss.cli.main import main as cli_main


def _write_app(tmp_path: Path, *, capabilities: tuple[str, ...] = ()) -> Path:
    cap_block = ""
    if capabilities:
        joined = "\n".join(f"  {item}" for item in capabilities)
        cap_block = f"capabilities:\n{joined}\n\n"
    app = tmp_path / "app.ai"
    app.write_text(
        f'spec is "1.0"\n\n{cap_block}flow "demo":\n  return "ok"\n\npage "home":\n  button "Run":\n    calls flow "demo"\n',
        encoding="utf-8",
    )
    return app


def _write_theme_app(tmp_path: Path) -> Path:
    app = tmp_path / "app.ai"
    app.write_text(
        'spec is "1.0"\n\n'
        "capabilities:\n"
        "  custom_theme\n\n"
        "theme:\n"
        '  preset: "clarity"\n'
        "  brand_palette:\n"
        '    brand_primary: "#6750A4"\n'
        "  tokens:\n"
        "    color.primary: color.brand_primary.600\n\n"
        'flow "demo":\n'
        '  return "ok"\n\n'
        'page "home":\n'
        "  card:\n"
        '    text is "Hello"\n',
        encoding="utf-8",
    )
    return app


def test_create_plugin_and_ui_pack_support_dry_run(tmp_path: Path, capsys, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    assert cli_main(["create", "plugin", "charts", "--dry-run", "--json"]) == 0
    plugin_payload = json.loads(capsys.readouterr().out)
    assert plugin_payload["ok"] is True
    assert plugin_payload["dry_run"] is True
    assert (tmp_path / "charts").exists() is False
    assert "plugin.json" in plugin_payload["files"]

    assert cli_main(["create", "ui_pack", "ops_dash", "--dry-run", "--json"]) == 0
    pack_payload = json.loads(capsys.readouterr().out)
    assert pack_payload["ok"] is True
    assert pack_payload["dry_run"] is True
    assert "pack.json" in pack_payload["files"]
    assert (tmp_path / "ui_packs" / "ops_dash").exists() is False


def test_create_plugin_writes_files(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    assert cli_main(["create", "plugin", "maps"]) == 0
    plugin_root = tmp_path / "maps"
    assert (plugin_root / "plugin.json").exists()
    assert (plugin_root / "renderer.py").exists()
    assert (plugin_root / "tests" / "test_plugin_manifest.py").exists()


def test_manifest_command_outputs_compiled_manifest(tmp_path: Path, capsys, monkeypatch) -> None:
    _write_app(tmp_path)
    monkeypatch.chdir(tmp_path)
    assert cli_main(["manifest", "app.ai", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["manifest"]["pages"]
    assert payload["manifest"]["actions"]


def test_validate_theme_command_reports_token_summary(tmp_path: Path, capsys, monkeypatch) -> None:
    _write_theme_app(tmp_path)
    monkeypatch.chdir(tmp_path)
    assert cli_main(["validate", "theme", "app.ai", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["theme"]["token_count"] > 0
    assert payload["theme"]["brand_palette_size"] == 1


def test_plugin_registry_publish_install_and_list(tmp_path: Path, capsys, monkeypatch) -> None:
    _write_app(tmp_path, capabilities=("plugin_registry",))
    monkeypatch.chdir(tmp_path)

    assert cli_main(["create", "plugin", "charts"]) == 0
    capsys.readouterr()
    assert cli_main(["publish", "plugin", str(tmp_path / "charts"), "--json"]) == 0
    publish_payload = json.loads(capsys.readouterr().out)
    assert publish_payload["ok"] is True
    assert publish_payload["name"] == "charts"

    assert cli_main(["list", "plugins", "--json"]) == 0
    list_payload = json.loads(capsys.readouterr().out)
    assert list_payload["count"] == 1
    assert list_payload["plugins"][0]["name"] == "charts"

    assert cli_main(["install", "plugin", "charts@0.1.0", "--json"]) == 0
    install_payload = json.loads(capsys.readouterr().out)
    assert install_payload["ok"] is True
    assert (tmp_path / "ui_plugins" / "charts" / "plugin.json").exists()


def test_plugin_registry_commands_require_capability(tmp_path: Path, capsys, monkeypatch) -> None:
    _write_app(tmp_path, capabilities=())
    monkeypatch.chdir(tmp_path)
    assert cli_main(["create", "plugin", "charts"]) == 0
    rc = cli_main(["publish", "plugin", str(tmp_path / "charts")])
    err = capsys.readouterr().err
    assert rc == 1
    assert "plugin_registry" in err
