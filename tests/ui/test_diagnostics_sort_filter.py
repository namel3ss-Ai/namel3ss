from __future__ import annotations

from pathlib import Path


def test_diagnostics_renderer_includes_sort_and_filter_controls() -> None:
    js = Path("src/namel3ss/studio/web/ui_renderer_diagnostics.js").read_text(encoding="utf-8")
    assert "Sort by" in js
    assert "{ value: \"severity\", label: \"severity\" }" in js
    assert "{ value: \"semantic_score\", label: \"semantic score\" }" in js
    assert "{ value: \"lexical_score\", label: \"lexical score\" }" in js
    assert "{ value: \"final_score\", label: \"final score\" }" in js
    assert "{ value: \"doc_id\", label: \"doc id\" }" in js
    assert "[\"semantic\", \"lexical\", \"final\"]" in js
    assert "compareScoreOrdering" in js
    assert "tieBreakSort" in js


def test_diagnostics_sort_filter_styles_exist() -> None:
    css = Path("src/namel3ss/studio/web/studio_ui.css").read_text(encoding="utf-8")
    assert ".ui-diagnostics-controls" in css
    assert ".ui-diagnostics-select" in css
    assert ".ui-diagnostics-toggle" in css
    assert ".ui-diagnostics-metrics" in css
    assert ".ui-diagnostics-filter-empty" in css

