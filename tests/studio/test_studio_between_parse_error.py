from __future__ import annotations

from namel3ss.studio.api import get_summary_payload


def test_studio_between_parse_error_payload(tmp_path):
    source = (
        'spec is "1.0"\n\n'
        'flow "demo":\n'
        "  if value is between min_val max_val:\n"
        "    return true\n"
    )
    app_path = tmp_path / "app.ai"
    payload = get_summary_payload(source, app_path.as_posix())
    assert payload.get("ok") is False
    assert payload.get("kind") == "parse"
    location = payload.get("location") or {}
    assert location.get("line") == 4
