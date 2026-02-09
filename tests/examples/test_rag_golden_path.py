from __future__ import annotations

import json
from pathlib import Path

from namel3ss.module_loader import load_project
from namel3ss.runtime.contracts.validate_payload import validate_contract_payload


EXAMPLE_ROOT = Path("examples/rag_chat_headless")


def test_rag_headless_example_files_exist() -> None:
    assert (EXAMPLE_ROOT / "README.md").exists()
    assert (EXAMPLE_ROOT / "app.ai").exists()
    assert (EXAMPLE_ROOT / "client.ts").exists()
    assert (EXAMPLE_ROOT / "headless_ui_response.json").exists()
    assert (EXAMPLE_ROOT / "headless_action_response.json").exists()


def test_rag_headless_example_app_parses() -> None:
    project = load_project(EXAMPLE_ROOT / "app.ai")
    page_names = [page.name for page in getattr(project.program, "pages", ())]
    assert "RAG" in page_names


def test_rag_headless_example_payloads_match_contracts() -> None:
    ui_payload = json.loads((EXAMPLE_ROOT / "headless_ui_response.json").read_text(encoding="utf-8"))
    action_payload = json.loads((EXAMPLE_ROOT / "headless_action_response.json").read_text(encoding="utf-8"))

    ui_warnings = validate_contract_payload(ui_payload, schema_name="headless_ui_response")
    action_warnings = validate_contract_payload(action_payload, schema_name="headless_action_response")

    assert ui_warnings == []
    assert action_warnings == []


def test_rag_headless_readme_describes_golden_path() -> None:
    text = (EXAMPLE_ROOT / "README.md").read_text(encoding="utf-8")
    for token in [
        "Upload",
        "ingestion",
        "chat",
        "citations",
        "trust indicator",
        "contract_version",
        "runtime-ui@1",
    ]:
        assert token in text
