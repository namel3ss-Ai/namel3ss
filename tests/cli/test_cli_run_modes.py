import os

import pytest

from namel3ss.cli.run_entry import dispatch_run_command
from namel3ss.errors.base import Namel3ssError


def test_dispatch_run_defaults_to_production_mode(monkeypatch):
    seen: dict[str, object] = {}

    def fake_run(args, *, ui_mode=None, diagnostics_enabled=None):
        seen["args"] = list(args)
        seen["mode"] = ui_mode
        seen["env_mode"] = os.getenv("N3_UI_MODE")
        seen["diagnostics"] = diagnostics_enabled
        return 7

    monkeypatch.setattr("namel3ss.cli.run_entry.run_run_command", fake_run)
    code = dispatch_run_command(["app.ai", "--dry"])

    assert code == 7
    assert seen["args"] == ["app.ai", "--dry"]
    assert seen["mode"] == "production"
    assert seen["env_mode"] == "production"
    assert seen["diagnostics"] is False


def test_dispatch_run_accepts_studio_subcommand(monkeypatch):
    seen: dict[str, object] = {}

    def fake_studio(path, port, dry):
        seen["path"] = path
        seen["port"] = port
        seen["dry"] = dry
        return 0

    monkeypatch.setattr("namel3ss.cli.run_entry.run_studio", fake_studio)
    code = dispatch_run_command(["studio", "app.ai", "--dry"])

    assert code == 0
    assert seen["path"] == "app.ai"
    assert seen["port"] == 7333
    assert seen["dry"] is True


def test_dispatch_run_ignores_env_mode_without_explicit_studio(monkeypatch):
    seen: dict[str, object] = {}

    def fake_run(args, *, ui_mode=None, diagnostics_enabled=None):
        seen["args"] = list(args)
        seen["mode"] = ui_mode
        seen["env_mode"] = os.getenv("N3_UI_MODE")
        seen["diagnostics"] = diagnostics_enabled
        return 0

    monkeypatch.setenv("N3_UI_MODE", "studio")
    monkeypatch.setattr("namel3ss.cli.run_entry.run_run_command", fake_run)
    code = dispatch_run_command(["app.ai", "--dry"])

    assert code == 0
    assert seen["args"] == ["app.ai", "--dry"]
    assert seen["mode"] == "production"
    assert seen["env_mode"] == "production"
    assert seen["diagnostics"] is False
    assert os.getenv("N3_UI_MODE") == "studio"


def test_dispatch_run_mode_flags_override_env(monkeypatch):
    seen: dict[str, object] = {}

    def fake_run(args, *, ui_mode=None, diagnostics_enabled=None):
        seen["args"] = list(args)
        seen["mode"] = ui_mode
        seen["env_mode"] = os.getenv("N3_UI_MODE")
        seen["diagnostics"] = diagnostics_enabled
        return 0

    monkeypatch.setenv("N3_UI_MODE", "studio")
    monkeypatch.setattr("namel3ss.cli.run_entry.run_run_command", fake_run)
    dispatch_run_command(["--production", "app.ai"])

    assert seen["args"] == ["app.ai"]
    assert seen["mode"] == "production"
    assert seen["env_mode"] == "production"
    assert seen["diagnostics"] is False
    assert os.getenv("N3_UI_MODE") == "studio"


def test_dispatch_run_unknown_mode_errors():
    with pytest.raises(Namel3ssError) as exc:
        dispatch_run_command(["invalidmode", "app.ai"])
    text = str(exc.value)
    assert "Unknown run mode 'invalidmode'" in text
    assert "n3 run studio app.ai" in text


def test_dispatch_run_rejects_conflicting_mode_flags():
    with pytest.raises(Namel3ssError) as exc:
        dispatch_run_command(["--studio", "--production", "app.ai"])
    assert "Use either --studio or --production, not both." in str(exc.value)


def test_dispatch_run_sets_diagnostics_flag(monkeypatch):
    seen: dict[str, object] = {}

    def fake_run(args, *, ui_mode=None, diagnostics_enabled=None):
        seen["args"] = list(args)
        seen["mode"] = ui_mode
        seen["env_mode"] = os.getenv("N3_UI_MODE")
        seen["diagnostics"] = diagnostics_enabled
        seen["env_diagnostics"] = os.getenv("N3_UI_DIAGNOSTICS")
        return 0

    monkeypatch.setattr("namel3ss.cli.run_entry.run_run_command", fake_run)
    code = dispatch_run_command(["app.ai", "--diagnostics"])

    assert code == 0
    assert seen["args"] == ["app.ai"]
    assert seen["mode"] == "production"
    assert seen["env_mode"] == "production"
    assert seen["diagnostics"] is True
    assert seen["env_diagnostics"] == "true"


def test_dispatch_run_allows_diagnostics_flag_in_studio(monkeypatch, capsys):
    seen: dict[str, object] = {}

    def fake_studio(path, port, dry):
        seen["path"] = path
        seen["port"] = port
        seen["dry"] = dry
        return 0

    monkeypatch.setattr("namel3ss.cli.run_entry.run_studio", fake_studio)
    code = dispatch_run_command(["studio", "app.ai", "--diagnostics"])
    captured = capsys.readouterr()

    assert code == 0
    assert seen["path"] == "app.ai"
    assert seen["port"] == 7333
    assert seen["dry"] is False
    assert captured.err == ""


def test_dispatch_run_rejects_runtime_flags_in_studio_mode():
    with pytest.raises(Namel3ssError) as exc:
        dispatch_run_command(["studio", "app.ai", "--target", "service"])
    assert "Unsupported flag '--target' for Studio mode." in str(exc.value)
