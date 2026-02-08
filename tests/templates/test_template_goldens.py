from __future__ import annotations

import json
import re
from pathlib import Path

from namel3ss.studio.api import get_ui_payload
from namel3ss.studio.session import SessionState

TEMPLATE_ROOT = Path("src/namel3ss/templates")
TEMPLATES = sorted(
    [path for path in TEMPLATE_ROOT.iterdir() if path.is_dir() and (path / "app.ai").exists()],
    key=lambda p: p.name,
)


def _assert_no_host_paths(payload: dict) -> None:
    text = json.dumps(payload, ensure_ascii=True)
    forbidden = [
        re.compile(r"[A-Za-z]:\\\\"),
        re.compile(r"/Users/"),
        re.compile(r"/home/"),
    ]
    for pattern in forbidden:
        assert pattern.search(text) is None


def test_templates_expected_ui_matches_manifest() -> None:
    assert TEMPLATES
    for template in TEMPLATES:
        app_path = template / "app.ai"
        expected_path = template / "expected_ui.json"
        source = app_path.read_text(encoding="utf-8")

        payload_first = get_ui_payload(source, SessionState(), app_path=app_path.as_posix())
        payload_second = get_ui_payload(source, SessionState(), app_path=app_path.as_posix())
        assert payload_first == payload_second

        expected = json.loads(expected_path.read_text(encoding="utf-8"))
        assert payload_first == expected
        _assert_no_host_paths(payload_first)
