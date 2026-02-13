from __future__ import annotations

from pathlib import Path


def test_observability_renderer_scripts_and_wiring() -> None:
    html = Path("src/namel3ss/studio/web/index.html").read_text(encoding="utf-8")
    assert "/observability/renderer.js" in html

    renderer = Path("src/namel3ss/studio/web/ui_renderer.js").read_text(encoding="utf-8")
    assert 'el.type === "observability_panel"' in renderer
    assert "renderObservabilityPanel(el, handleAction)" in renderer
    assert "renderObservabilityPanel({ type: \"observability_panel\", explain: el }, handleAction)" in renderer

    panel = Path("src/namel3ss/studio/web/observability/renderer.js").read_text(encoding="utf-8")
    assert "renderObservabilityPanel" in panel
    assert "Observability" in panel
    assert "Trace timeline" in panel
    assert "renderRetrievalExplainElement" in panel
    assert "renderRetrievalTracePanel" in panel


__all__ = []
