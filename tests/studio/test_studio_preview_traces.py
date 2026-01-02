from pathlib import Path


def test_action_result_helper_wiring():
    js = Path("src/namel3ss/studio/web/studio/action_result.js").read_text(encoding="utf-8")
    assert "applyActionResult" in js
    assert "setCachedTraces" in js
    assert "renderTraces" in js
    assert "renderMemory" in js
    assert "renderErrors" in js
    run_js = Path("src/namel3ss/studio/web/studio/run.js").read_text(encoding="utf-8")
    assert "applyActionResult" in run_js
