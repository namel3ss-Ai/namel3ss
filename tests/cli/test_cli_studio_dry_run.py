from namel3ss.cli.main import main


SOURCE = 'spec is "1.0"\n\nflow "demo":\n  return "ok"\n'


def test_studio_dry_run(tmp_path, capsys):
    path = tmp_path / "app.ai"
    path.write_text(SOURCE, encoding="utf-8")
    code = main([str(path), "studio", "--dry"])
    out = capsys.readouterr().out
    assert code == 0
    assert "Studio: http://127.0.0.1:" in out
