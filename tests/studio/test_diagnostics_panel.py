from __future__ import annotations

from pathlib import Path

from namel3ss.studio.diagnostics.panel_model import build_diagnostics_panel_payload


def test_diagnostics_panel_aggregates_and_orders_entries() -> None:
    manifest = {
        "contract_warnings": [
            {
                "code": "schema.type_mismatch",
                "path": "$.state",
                "message": "Expected object.",
            }
        ],
        "capabilities_enabled": [
            {"name": "http_client", "version": "1.0.0", "required_permissions": ["network"]},
        ],
    }
    state_snapshot = {
        "ingestion": {
            "upload-1": {
                "status": "block",
                "reasons": ["empty_text"],
                "reason_details": [
                    {
                        "code": "empty_text",
                        "message": "No extractable text.",
                        "remediation": "Run OCR or upload a text PDF.",
                    }
                ],
            }
        }
    }
    runtime_errors = [
        {
            "category": "runtime_internal",
            "message": "Runtime crashed.",
            "hint": "Retry the action.",
            "origin": "runtime",
            "stable_code": "runtime.runtime_internal.crash",
        }
    ]
    run_artifact = {
        "run_id": "run-1",
        "inputs": {"payload": {}, "state": {}},
        "retrieval_trace": [],
        "prompt": {"text": "", "hash": ""},
        "capability_usage": [],
        "output": {},
        "checksums": {},
    }

    payload = build_diagnostics_panel_payload(
        manifest=manifest,
        state_snapshot=state_snapshot,
        runtime_errors=runtime_errors,
        run_artifact=run_artifact,
    )
    entries = payload["entries"]
    assert payload["schema_version"] == "studio_diagnostics@1"
    assert entries
    assert entries[0]["severity"] == "error"
    assert any(item["category"] == "ingestion" for item in entries)
    assert any(item["category"] == "contract_warning" for item in entries)
    assert any(item["category"] == "capability" for item in entries)
    assert any(item["category"] == "audit_replay" for item in entries)


def test_diagnostics_renderers_wired_in_studio() -> None:
    html = Path("src/namel3ss/studio/web/index.html").read_text(encoding="utf-8")
    assert "/ui_renderer_diagnostics.js" in html
    assert "/ui_renderer_run_diff.js" in html

    ui_renderer = Path("src/namel3ss/studio/web/ui_renderer.js").read_text(encoding="utf-8")
    assert 'el.type === "diagnostics_panel"' in ui_renderer
    assert "renderDiagnosticsElement" in ui_renderer
    assert 'el.type === "run_diff"' in ui_renderer
    assert "renderRunDiffElement" in ui_renderer

    diagnostics_renderer = Path("src/namel3ss/studio/web/ui_renderer_diagnostics.js").read_text(encoding="utf-8")
    assert "Unified Diagnostics" in diagnostics_renderer
    assert "No diagnostics found." in diagnostics_renderer

    run_diff_renderer = Path("src/namel3ss/studio/web/ui_renderer_run_diff.js").read_text(encoding="utf-8")
    assert "Run Comparison" in run_diff_renderer
    assert "No run diff available yet." in run_diff_renderer

    css = Path("src/namel3ss/studio/web/studio_ui.css").read_text(encoding="utf-8")
    assert ".ui-diagnostics-panel" in css
    assert ".ui-run-diff" in css
