from __future__ import annotations

from namel3ss.cli.main import main


def test_cli_bundle_help_is_stable(capsys) -> None:
    assert main(["bundle", "--help"]) == 0
    out = capsys.readouterr().out
    assert "Usage:" in out
    assert "n3 build [app.ai]" in out
    assert "--profile-iterations" in out


def test_cli_deploy_help_is_stable(capsys) -> None:
    assert main(["deploy", "--help"]) == 0
    out = capsys.readouterr().out
    assert "Usage:" in out
    assert "n3 deploy [archive.n3bundle.zip]" in out
    assert "--channel" in out
