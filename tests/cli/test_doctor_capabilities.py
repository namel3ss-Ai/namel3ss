import json

from namel3ss.cli.main import main as cli_main


def test_doctor_reports_unknown_capability_override(tmp_path, monkeypatch, capsys):
    app_source = 'spec is "1.0"\n\nflow "demo":\n  return "ok"\n'
    (tmp_path / "app.ai").write_text(app_source, encoding="utf-8")
    (tmp_path / "namel3ss.toml").write_text(
        '[capability_overrides]\n"unknown tool" = { no_network = true }\n',
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    rc = cli_main(["doctor", "--json"])
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    checks = {c["id"]: c for c in data["checks"]}
    check = checks["capability_overrides"]
    assert check["status"] == "error"
    assert "unknown tool" in check["message"]
