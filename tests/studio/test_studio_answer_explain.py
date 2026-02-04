from __future__ import annotations

from pathlib import Path


def test_explain_panel_supports_answer_explain() -> None:
    js = Path("src/namel3ss/studio/web/studio/explain.js").read_text(encoding="utf-8")
    assert "answer_explain" in js
    assert "renderExplain" in js
