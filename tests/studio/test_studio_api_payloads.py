from namel3ss.studio import api


SOURCE = '''spec is "1.0"

record "User":
  name string

flow "one":
  return "ok"

page "home":
  button "Run":
    calls flow "one"
  form is "User"
'''


def test_summary_ui_actions_lint_payloads(tmp_path):
    app_file = tmp_path / "app.ai"
    app_file.write_text(SOURCE, encoding="utf-8")
    summary = api.get_summary_payload(SOURCE, app_file.as_posix())
    assert summary["ok"] is True
    assert summary["counts"]["flows"] == 1

    ui = api.get_ui_payload(SOURCE, app_path=app_file.as_posix())
    assert "pages" in ui
    actions = api.get_actions_payload(SOURCE, app_path=app_file.as_posix())
    assert actions["ok"] is True
    ids = [a["id"] for a in actions["actions"]]
    assert ids == sorted(ids)
    lint = api.get_lint_payload(SOURCE)
    assert "findings" in lint
    diagnostics = api.get_diagnostics_payload(SOURCE, app_file.as_posix())
    assert diagnostics["ok"] is True
    assert "diagnostics" in diagnostics


def test_error_payload_includes_caret():
    bad_source = 'spec is "1.0"\n\nflow "demo"\n  return "ok"\n'
    summary = api.get_summary_payload(bad_source, "bad.ai")
    assert summary["ok"] is False
    assert "^" in summary["error"]
