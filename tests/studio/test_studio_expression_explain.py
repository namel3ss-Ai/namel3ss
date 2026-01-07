from __future__ import annotations

from pathlib import Path

from namel3ss.studio.api import execute_action
from namel3ss.studio.session import SessionState


APP_SOURCE = '''spec is "1.0"

flow "demo":
  let numbers is list:
    1
    2
  calc:
    total = sum(numbers)
  return total

page "home":
  button "Run":
    calls flow "demo"
'''.lstrip()


def test_action_payload_includes_expression_explain(tmp_path: Path) -> None:
    app_file = tmp_path / "app.ai"
    app_file.write_text(APP_SOURCE, encoding="utf-8")
    session = SessionState()

    response = execute_action(
        APP_SOURCE,
        session,
        "page.home.button.run",
        {},
        app_path=app_file.as_posix(),
    )
    traces = response.get("traces") or []
    assert any(trace.get("type") == "expression_explain" for trace in traces if isinstance(trace, dict))


def test_explain_panel_module_present() -> None:
    js = Path("src/namel3ss/studio/web/studio/explain.js").read_text(encoding="utf-8")
    assert "expression_explain" in js
    assert "renderExplain" in js
