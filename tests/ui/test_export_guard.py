from __future__ import annotations

from namel3ss.ui.export.actions import build_actions_export
from namel3ss.ui.export.guard import filter_export_actions


def test_filter_export_actions_omits_debug_and_unsupported_entries() -> None:
    actions = {
        "app.retrieval": {"id": "app.retrieval", "type": "retrieval_run", "debug_only": True},
        "app.retrieval.tuning.set_semantic_k": {
            "id": "app.retrieval.tuning.set_semantic_k",
            "type": "call_flow",
            "flow": "set_semantic_k",
            "input_field": "k",
            "debug_only": True,
            "system_action": "retrieval_tuning",
        },
        "page.home.button.run": {"id": "page.home.button.run", "type": "call_flow", "flow": "run"},
    }
    filtered, skipped = filter_export_actions(actions)
    assert list(filtered.keys()) == ["page.home.button.run"]
    assert [entry["id"] for entry in skipped] == [
        "app.retrieval",
        "app.retrieval.tuning.set_semantic_k",
    ]


def test_build_actions_export_reports_skipped_actions() -> None:
    manifest = {
        "actions": {
            "page.home.button.run": {"id": "page.home.button.run", "type": "call_flow", "flow": "run"},
            "app.retrieval": {"id": "app.retrieval", "type": "retrieval_run", "debug_only": True},
        }
    }
    exported = build_actions_export(manifest)
    assert exported["schema_version"] == "1"
    assert exported["actions"] == [{"id": "page.home.button.run", "type": "call_flow", "flow": "run"}]
    assert exported["skipped"] == [{"id": "app.retrieval", "reason": "debug_only"}]
