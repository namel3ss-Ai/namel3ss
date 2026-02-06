from __future__ import annotations

from pathlib import Path

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.feedback import append_feedback_entry, load_feedback_entries, summarize_feedback



def _write_app(tmp_path: Path) -> Path:
    app = tmp_path / "app.ai"
    app.write_text('spec is "1.0"\n\nflow "demo":\n  return "ok"\n', encoding="utf-8")
    return app



def test_feedback_append_and_load_is_deterministic(tmp_path: Path) -> None:
    app = _write_app(tmp_path)
    append_feedback_entry(
        app.parent,
        app,
        flow_name="ask_ai",
        input_id="a1",
        rating="good",
        comment="clear answer",
    )
    append_feedback_entry(
        app.parent,
        app,
        flow_name="ask_ai",
        input_id="a2",
        rating="bad",
        comment="",
        step_count=5,
    )
    entries = load_feedback_entries(app.parent, app)
    assert [entry.step_count for entry in entries] == [1, 5]
    assert [entry.rating for entry in entries] == ["good", "bad"]



def test_feedback_summary_computes_ratios(tmp_path: Path) -> None:
    app = _write_app(tmp_path)
    append_feedback_entry(app.parent, app, flow_name="ask_ai", input_id="a1", rating="excellent")
    append_feedback_entry(app.parent, app, flow_name="ask_ai", input_id="a2", rating="good")
    append_feedback_entry(app.parent, app, flow_name="ask_ai", input_id="a3", rating="bad")
    summary = summarize_feedback(load_feedback_entries(app.parent, app))
    assert summary["total"] == 3
    assert summary["positive_ratio"] == pytest.approx(2 / 3)
    assert summary["completion_quality"] == pytest.approx((1.0 + 0.8 + 0.0) / 3)



def test_feedback_rejects_invalid_rating(tmp_path: Path) -> None:
    app = _write_app(tmp_path)
    with pytest.raises(Namel3ssError):
        append_feedback_entry(app.parent, app, flow_name="ask_ai", input_id="a1", rating="ok")
