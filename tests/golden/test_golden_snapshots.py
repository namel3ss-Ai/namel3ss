from __future__ import annotations

import os

from tests.golden.harness import load_manifest, run_golden_app, write_snapshots

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
        write_snapshots(app.app_id, snapshot, update=update)


def test_golden_coverage_guard() -> None:
    apps = load_manifest()
    assert 20 <= len(apps) <= 50, "golden suite should contain 20-50 apps"
    tags = {tag for app in apps for tag in app.tags}
    missing = sorted(REQUIRED_TAGS - tags)
    assert not missing, f"golden suite missing tags: {', '.join(missing)}"
