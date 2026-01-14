from __future__ import annotations

from namel3ss.cli.main import main


def test_check_reports_reserved_identifier_hint(tmp_path, capsys):
    app = tmp_path / "app.ai"
    app.write_text('spec is "1.0"\n\nflow "demo":\n  let title is "x"\n', encoding="utf-8")
    exit_code = main([str(app), "check"])
    captured = capsys.readouterr()
    assert exit_code == 1
    out = captured.out
    assert "Parse: FAIL" in out
    assert "reserved keyword" in out.lower()
    assert "title" in out
    assert "Hint: 'title' is reserved" in out
    assert "ticket_title" in out
