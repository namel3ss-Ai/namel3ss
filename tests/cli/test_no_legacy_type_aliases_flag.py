from pathlib import Path

from namel3ss.cli.main import main as cli_main


def test_check_fails_with_no_legacy_alias_flag(tmp_path: Path):
    app = tmp_path / "alias.ai"
    app.write_text(
        'record "User":\n'
        '  field "age" is int\n',
        encoding="utf-8",
    )
    rc = cli_main([str(app), "check", "--no-legacy-type-aliases"])
    assert rc != 0
