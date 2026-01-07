from __future__ import annotations

from pathlib import Path

import pytest

from namel3ss.studio.api import execute_action, get_summary_payload
from namel3ss.studio.session import SessionState


def test_studio_reduce_parse_error_location(tmp_path: Path) -> None:
    source = (
        'spec is "1.0"\n\n'
        'flow "demo":\n'
        "  let total is reduce numbers with acc as s and item as n:\n"
        "    s + n\n"
    )
    app_path = tmp_path / "app.ai"
    payload = get_summary_payload(source, app_path.as_posix())
    assert payload.get("ok") is False
    assert payload.get("kind") == "parse"
    location = payload.get("location") or {}
    assert location.get("line") == 4


@pytest.mark.parametrize(
    "payload, expected_line",
    [
        ({"values": 10}, 4),
        ({"values": ["x"]}, 5),
    ],
)
def test_studio_reduce_runtime_error_location(tmp_path: Path, payload: dict, expected_line: int) -> None:
    source = (
        'spec is "1.0"\n\n'
        'flow "demo":\n'
        "  return reduce input.values with acc as s and item as n starting 0:\n"
        "    s + n\n\n"
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
    assert location.get("line") == expected_line
