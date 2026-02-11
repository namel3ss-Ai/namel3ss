from __future__ import annotations

from pathlib import Path

from namel3ss.studio.panels.context_inspector import build_context_inspector_payload


SOURCE = '''
spec is "1.0"

ai "assistant":
  provider is "mock"
  model is "mock-model"

flow "ask_ai":
  ask ai "assistant" with input: "Summarize order signals." as reply
  return reply

page "home":
  button "Ask":
    calls flow "ask_ai"
'''.lstrip()


def test_context_inspector_payload_is_studio_only_and_deterministic(tmp_path: Path) -> None:
    app_file = tmp_path / "app.ai"
    app_file.write_text(SOURCE, encoding="utf-8")

    state_snapshot = {
        "active_docs": ["doc-b", "doc-a", "doc-b"],
        "retrieval": {
            "tuning": {
                "semantic_k": 12,
                "lexical_k": 8,
                "final_top_k": 5,
                "semantic_weight": 0.65,
            }
        },
    }
    run_artifact = {
        "output": {
            "traces": [
                {"type": "tool_call", "tool": "fetch", "status": "ok"},
                {"ai_name": "assistant", "input": "Orders: A/B/C\nQuestion: What changed?"},
            ]
        }
    }

    first = build_context_inspector_payload(
        source=SOURCE,
        app_path=app_file.as_posix(),
        state_snapshot=state_snapshot,
        run_artifact=run_artifact,
    )
    second = build_context_inspector_payload(
        source=SOURCE,
        app_path=app_file.as_posix(),
        state_snapshot=state_snapshot,
        run_artifact=run_artifact,
    )

    assert first == second
    assert first["studio_only"] is True
    assert first["filter_tags"] == ["doc-a", "doc-b"]
    assert list(first["retrieval_settings"].keys()) == ["semantic_k", "lexical_k", "final_top_k", "semantic_weight"]
    assert first["runtime_prompt_preview"] == "Orders: A/B/C\nQuestion: What changed?"
    assert first["compiled_prompt_context"] == [{"flow": "ask_ai", "prompt_preview": "Summarize order signals."}]


def test_context_inspector_renderer_wiring_and_studio_only_gate_exist() -> None:
    diagnostics_js = Path("src/namel3ss/studio/web/studio/diagnostics.js").read_text(encoding="utf-8")
    renderer_js = Path("src/namel3ss/studio/web/ui_renderer.js").read_text(encoding="utf-8")

    assert "renderContextInspectorSection" in diagnostics_js
    assert "Context Inspector (Studio)" in diagnostics_js
    assert "runtime_prompt_preview" in diagnostics_js
    assert 'el.studio_only === true && manifest.mode !== "studio"' in renderer_js

