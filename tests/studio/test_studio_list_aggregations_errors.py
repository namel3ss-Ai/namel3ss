from __future__ import annotations

from pathlib import Path

import pytest

from namel3ss.studio.api import execute_action
from namel3ss.studio.session import SessionState


@pytest.mark.parametrize(
    "payload",
    [
        {"numbers": []},
        {"numbers": [1, "oops"]},
        {"numbers": 10},
    ],
)
def test_studio_list_aggregation_runtime_error_payloads(tmp_path: Path, payload: dict) -> None:
    source = (
        'spec is "1.0"\n\n'
        'flow "demo":\n'
        "  return sum(input.numbers)\n\n"
        'page "home":\n'
        '  button "Run":\n'
        '    calls flow "demo"\n'
    )
    app_path = tmp_path / "app.ai"
    app_path.write_text(source, encoding="utf-8")
    session = SessionState()
    response = execute_action(
        source,
        session,
        "page.home.button.run",
        payload,
        app_path=app_path.as_posix(),
    )
    assert response.get("ok") is False
    assert response.get("kind") == "runtime"
    location = response.get("location") or {}
    assert location.get("line") == 4
