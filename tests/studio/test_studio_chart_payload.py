from __future__ import annotations

from pathlib import Path

from namel3ss.studio.api import get_ui_payload
from namel3ss.studio.session import SessionState


APP_SOURCE = '''
spec is "1.0"

record "Metric":
  name text
  value number

page "home":
  table is "Metric"
  chart is "Metric":
    type is bar
    x is name
    y is value
'''.lstrip()


def test_studio_chart_payload_is_deterministic(tmp_path: Path) -> None:
    app_file = tmp_path / "app.ai"
    app_file.write_text(APP_SOURCE, encoding="utf-8")
    session = SessionState()
    first = get_ui_payload(APP_SOURCE, session, app_path=app_file.as_posix())
    second = get_ui_payload(APP_SOURCE, session, app_path=app_file.as_posix())
    assert first == second
    chart = next(
        el
        for page in first.get("pages", [])
        for el in page.get("elements", [])
        if el.get("type") == "chart"
    )
    assert chart["chart_type"] == "bar"
    assert chart["x"] == "name"
    assert chart["y"] == "value"
