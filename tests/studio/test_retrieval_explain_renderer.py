from pathlib import Path


def test_retrieval_explain_renderer_scripts_and_wiring() -> None:
    html = Path("src/namel3ss/studio/web/index.html").read_text(encoding="utf-8")
    assert "/ui_renderer_retrieval_explain.js" in html

    renderer = Path("src/namel3ss/studio/web/ui_renderer.js").read_text(encoding="utf-8")
    assert 'el.type === "retrieval_explain"' in renderer
    assert "renderRetrievalExplainElement" in renderer

    retrieval_renderer = Path("src/namel3ss/studio/web/ui_renderer_retrieval_explain.js").read_text(encoding="utf-8")
    assert "renderRetrievalExplainElement" in retrieval_renderer
    assert "Why this answer?" in retrieval_renderer
    assert "ui-retrieval-explain-trace" in retrieval_renderer


def test_retrieval_explain_renderer_css_contract() -> None:
    css = Path("src/namel3ss/studio/web/studio_ui.css").read_text(encoding="utf-8")
    for selector in [
        ".ui-retrieval-explain",
        ".ui-retrieval-explain-trust-badge",
        ".ui-retrieval-explain-plan",
        ".ui-retrieval-explain-trace",
        ".ui-retrieval-explain-row",
    ]:
        assert selector in css


def test_retrieval_explain_renderer_snapshot_strings() -> None:
    renderer = Path("src/namel3ss/studio/web/ui_renderer_retrieval_explain.js").read_text(encoding="utf-8")
    assert "No retrieval evidence available." in renderer
    assert "Retrieved chunks" in renderer
    assert "Trust " in renderer
