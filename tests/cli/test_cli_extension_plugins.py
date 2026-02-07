from __future__ import annotations

import json
from pathlib import Path

from namel3ss.cli.main import main as cli_main


def _write_app(tmp_path: Path, *, capabilities: tuple[str, ...]) -> Path:
    cap_lines = "\n".join(f"  {item}" for item in capabilities)
    app = tmp_path / "app.ai"
    app.write_text(
        'spec is "1.0"\n\n'
        "capabilities:\n"
        f"{cap_lines}\n\n"
        'flow "demo":\n'
        '  return "ok"\n\n'
        'page "home":\n'
        '  button "Run":\n'
        '    calls flow "demo"\n',
        encoding="utf-8",
    )
    return app


def _write_registry_plugin(registry_root: Path, *, name: str, version: str) -> Path:
    plugin_dir = registry_root / name / version
    plugin_dir.mkdir(parents=True, exist_ok=True)
    (plugin_dir / "plugin.yaml").write_text(
        (
            f"name: {name}\n"
            f"version: \"{version}\"\n"
            "author: Community Author\n"
            "description: Community extension package\n"
            "permissions:\n"
            "  - ui\n"
            "hooks:\n"
            "  runtime: hooks/runtime.py\n"
            "module: renderer.py\n"
            "components:\n"
            "  - name: LineChart\n"
            "    props:\n"
            "      data: state_path\n"
        ),
        encoding="utf-8",
    )
    (plugin_dir / "renderer.py").write_text(
        "def render(props, state):\n    return [{\"type\": \"line_chart\", \"props\": props}]\n",
        encoding="utf-8",
    )
    (plugin_dir / "hooks").mkdir(exist_ok=True)
    (plugin_dir / "hooks" / "runtime.py").write_text(
        "def on_runtime_start(context):\n    return {\"ok\": True}\n",
        encoding="utf-8",
    )
    return plugin_dir


def test_plugin_search_and_info_show_extension_metadata(tmp_path: Path, capsys, monkeypatch) -> None:
    _write_app(tmp_path, capabilities=("extension_trust",))
    registry_root = tmp_path / "registry"
    _write_registry_plugin(registry_root, name="charts", version="1.2.0")
    monkeypatch.chdir(tmp_path)

    assert cli_main(["plugin", "search", "chart", "--registry", str(registry_root), "--json"]) == 0
    search_payload = json.loads(capsys.readouterr().out)
    assert search_payload["count"] == 1
    assert search_payload["results"][0]["name"] == "charts"
    assert search_payload["results"][0]["permissions"] == ["ui"]
    assert search_payload["results"][0]["trusted"] is False

    assert cli_main(["plugin", "info", "charts@1.2.0", "--registry", str(registry_root), "--json"]) == 0
    info_payload = json.loads(capsys.readouterr().out)
    assert info_payload["plugin"]["name"] == "charts"
    assert info_payload["plugin"]["version"] == "1.2.0"
    assert info_payload["plugin"]["hooks"] == {"runtime": "hooks/runtime.py"}


def test_plugin_install_requires_extension_trust_capability(tmp_path: Path, capsys, monkeypatch) -> None:
    _write_app(tmp_path, capabilities=("custom_ui", "sandbox"))
    registry_root = tmp_path / "registry"
    _write_registry_plugin(registry_root, name="charts", version="1.2.0")
    monkeypatch.chdir(tmp_path)

    code = cli_main(["plugin", "install", "charts@1.2.0", "--registry", str(registry_root), "--yes", "--json"])
    err = capsys.readouterr().err
    assert code == 1
    assert "extension_trust" in err


def test_plugin_install_trust_list_and_revoke(tmp_path: Path, capsys, monkeypatch) -> None:
    _write_app(tmp_path, capabilities=("extension_trust",))
    registry_root = tmp_path / "registry"
    _write_registry_plugin(registry_root, name="charts", version="1.2.0")
    monkeypatch.chdir(tmp_path)

    code = cli_main(["plugin", "install", "charts@1.2.0", "--registry", str(registry_root), "--json"])
    err = capsys.readouterr().err
    assert code == 1
    assert "not trusted" in err.lower()

    assert cli_main(["plugin", "install", "charts@1.2.0", "--registry", str(registry_root), "--yes", "--json"]) == 0
    install_payload = json.loads(capsys.readouterr().out)
    assert install_payload["ok"] is True
    assert install_payload["trusted"] is True
    assert (tmp_path / "ui_plugins" / "charts" / "plugin.yaml").exists()
    assert (tmp_path / ".namel3ss" / "trusted_extensions.yaml").exists()

    assert cli_main(["plugin", "list", "--installed", "--json"]) == 0
    installed_payload = json.loads(capsys.readouterr().out)
    assert installed_payload["count"] == 1
    assert installed_payload["plugins"][0]["trusted"] is True
    assert installed_payload["plugins"][0]["permissions"] == ["ui"]

    assert cli_main(["plugin", "revoke", "charts@1.2.0", "--json"]) == 0
    revoke_payload = json.loads(capsys.readouterr().out)
    assert revoke_payload["ok"] is True
    assert revoke_payload["removed"] == 1

    assert cli_main(["plugin", "list", "--installed", "--json"]) == 0
    installed_after_revoke = json.loads(capsys.readouterr().out)
    assert installed_after_revoke["plugins"][0]["trusted"] is False


def test_plugin_update_reports_when_already_current(tmp_path: Path, capsys, monkeypatch) -> None:
    _write_app(tmp_path, capabilities=("extension_trust",))
    registry_root = tmp_path / "registry"
    _write_registry_plugin(registry_root, name="charts", version="1.2.0")
    monkeypatch.chdir(tmp_path)

    assert cli_main(["plugin", "install", "charts@1.2.0", "--registry", str(registry_root), "--yes", "--json"]) == 0
    capsys.readouterr()
    assert cli_main(["plugin", "update", "charts", "--registry", str(registry_root), "--yes", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["updated"] is False
