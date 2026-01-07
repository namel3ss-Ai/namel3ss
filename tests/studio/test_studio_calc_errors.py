from __future__ import annotations

from pathlib import Path

from namel3ss.studio.api import get_summary_payload


def test_studio_calc_parse_error_location(tmp_path: Path) -> None:
    source = (
        'spec is "1.0"\n\n'
        'flow "demo":\n'
        "  calc:\n"
        "    total 1\n"
    )
    app_path = tmp_path / "app.ai"
    payload = get_summary_payload(source, app_path.as_posix())
    assert payload.get("ok") is False
    assert payload.get("kind") == "parse"
    location = payload.get("location") or {}
    assert location.get("line") == 5


def test_studio_calc_invalid_target_location(tmp_path: Path) -> None:
    source = (
        'spec is "1.0"\n\n'
        'flow "demo":\n'
        "  calc:\n"
        "    input.value = 1\n"
    )
    app_path = tmp_path / "app.ai"
    payload = get_summary_payload(source, app_path.as_posix())
    assert payload.get("ok") is False
    assert payload.get("kind") == "parse"
    location = payload.get("location") or {}
    assert location.get("line") == 5
