from __future__ import annotations

from namel3ss.cli.main import main as cli_main
from namel3ss.errors.render import format_error
from namel3ss.errors.base import Namel3ssError


def test_missing_app_file_message(tmp_path, capsys):
    missing = tmp_path / "missing.ai"
    rc = cli_main([str(missing), "check"])
    assert rc == 1
    out = capsys.readouterr().out
    assert "App file not found" in out
    assert "Fix" in out


def test_curly_brace_parse_error_message(capsys):
    from tempfile import NamedTemporaryFile

    with NamedTemporaryFile("w", suffix=".ai", delete=False) as tmp:
        tmp.write(
            "spec is \"1.0\"\n\nclassification \"bad\":\n"
            "  model is \"gpt-4\"\n"
            "  prompt is \"Tag\"\n"
            "  labels: [billing, {technical}]\n"
        )
        path = tmp.name
    rc = cli_main([path, "check"])
    assert rc == 1
    out = capsys.readouterr().out
    assert "nested grouping" in out.lower()


def test_strict_alias_rejection_message():
    try:
        from namel3ss.parser.core import parse

        parse('spec is "1.0"\n\nrecord "X":\n field "a" is int', allow_legacy_type_aliases=False)
    except Namel3ssError as err:
        msg = format_error(err, 'spec is "1.0"\n\nrecord "X":\n field "a" is int')
        assert "Use 'number'" in msg
        assert "Fix" in msg


def test_run_directory_path_reports_extension_error(tmp_path, capsys):
    app_dir = tmp_path / "demo"
    app_dir.mkdir()
    rc = cli_main(["run", str(app_dir)])
    captured = capsys.readouterr()
    combined = f"{captured.out}{captured.err}"
    assert rc == 1
    assert "namel3ss apps use the .ai extension." in combined
    assert "NameError: name 'sys' is not defined" not in combined
