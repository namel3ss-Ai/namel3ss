from __future__ import annotations

from pathlib import Path

from namel3ss.module_loader import load_project


APP_PATH = Path("apps/rag-application/app.ai")


def test_rag_application_example_exists_and_parses() -> None:
    assert APP_PATH.exists()
    source_lines = APP_PATH.read_text(encoding="utf-8").splitlines()
    non_empty_lines = [line for line in source_lines if line.strip()]
    assert len(non_empty_lines) <= 10
    project = load_project(APP_PATH)
    flow_names = [flow.name for flow in project.program.flows]
    assert "rag.answer" in flow_names
    assert "rag.ingest" in flow_names
