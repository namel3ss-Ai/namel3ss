from __future__ import annotations

import json
import os
from pathlib import Path

from tests._ci_debug import debug_context
from tests.golden.harness import SNAPSHOTS_DIR, load_manifest, run_golden_app, write_snapshots

REQUIRED_TAGS = {
    "agent_parallel",
    "agent_run",
    "ai_ask",
    "control_flow",
    "crud_create",
    "crud_delete",
    "crud_find",
    "crud_save",
    "crud_update",
    "error_capability",
    "error_parse",
    "error_provider",
    "error_runtime",
    "error_tool",
    "expressions",
    "flow_requires",
    "page_requires",
    "parallel",
    "tool",
    "ui_button",
    "ui_card",
    "ui_form",
    "ui_layout",
    "ui_section",
    "ui_table",
    "ui_text",
    "ui_title",
}


def test_golden_snapshots(tmp_path) -> None:
    update = os.getenv("UPDATE_SNAPSHOTS") == "1"
    apps = load_manifest()
    for app in apps:
        snapshot = run_golden_app(app, tmp_path / app.app_id)
        try:
            write_snapshots(app.app_id, snapshot, update=update)
        except AssertionError:
            if os.getenv("CI") == "true" and app.app_id == "tool_basic":
                _print_tool_basic_diff(snapshot, tmp_path / app.app_id)
            raise


def test_golden_coverage_guard() -> None:
    apps = load_manifest()
    assert 20 <= len(apps) <= 50, "golden suite should contain 20-50 apps"
    tags = {tag for app in apps for tag in app.tags}
    missing = sorted(REQUIRED_TAGS - tags)
    assert not missing, f"golden suite missing tags: {', '.join(missing)}"


def _print_tool_basic_diff(snapshot: dict[str, object], app_root: Path) -> None:
    expected_path = SNAPSHOTS_DIR / "tool_basic" / "run.json"
    if not expected_path.exists():
        print(json.dumps({"error": "missing expected snapshot", "path": str(expected_path)}, sort_keys=True))
        return
    expected = json.loads(expected_path.read_text(encoding="utf-8"))
    actual_run = snapshot.get("run") if isinstance(snapshot, dict) else None
    expected_trace = _first_tool_trace(expected)
    actual_trace = _first_tool_trace(actual_run)
    diff = _trace_diff(expected_trace, actual_trace)
    print(json.dumps(debug_context("golden_tool_basic", app_root=app_root), sort_keys=True))
    print(json.dumps(diff, sort_keys=True))


def _first_tool_trace(payload: object) -> dict[str, object]:
    if not isinstance(payload, dict):
        return {}
    traces = payload.get("traces")
    if not isinstance(traces, list):
        return {}
    for item in traces:
        if isinstance(item, dict) and item.get("type") == "tool_call":
            return item
    return {}


def _trace_diff(expected: dict[str, object], actual: dict[str, object]) -> dict[str, object]:
    fields = ["resolved_source", "entry", "python_path", "sandbox", "timeout_ms", "runner"]
    differences: dict[str, object] = {}
    for key in fields:
        if expected.get(key) != actual.get(key):
            differences[key] = {"expected": expected.get(key), "actual": actual.get(key)}
    return {"trace_diff": differences}
