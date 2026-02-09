from __future__ import annotations

import json
from pathlib import Path

from namel3ss.ui.manifest import build_manifest
from tests.conftest import lower_ir_program

FIXTURE_APP = Path("tests/fixtures/rag_ui_manifest_app.ai")
GOLDEN = Path("tests/fixtures/rag_ui_manifest_golden.json")

STATE = {
    "chat": {
        "messages": [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ],
        "citations": [
            {"title": "Doc A", "url": "https://example.com", "snippet": "Example snippet"},
        ],
    },
    "loading": False,
    "ui": {
        "show_drawer": True,
        "preview_source": {"title": "Doc A", "url": "https://example.com", "snippet": "Example snippet"},
    },
}


def test_rag_ui_manifest_matches_golden() -> None:
    program = lower_ir_program(FIXTURE_APP.read_text(encoding="utf-8"))
    manifest = build_manifest(program, state=dict(STATE), store=None)
    expected = json.loads(GOLDEN.read_text(encoding="utf-8"))
    assert manifest == expected
