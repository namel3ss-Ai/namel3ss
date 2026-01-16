from pathlib import Path


def test_foreign_boundary_doc_contract() -> None:
    text = Path("docs/tools.md").read_text(encoding="utf-8")
    required = [
        "Foreign boundaries (explicit extensions)",
        "foreign python function",
        "foreign js function",
        "call foreign",
        "Allowed types",
        "N3_FOREIGN_STRICT",
        "N3_FOREIGN_ALLOW",
        ".namel3ss/foreign",
        "boundary_start",
        "boundary_end",
        "foreign intent",
    ]
    for item in required:
        assert item in text, f"Missing '{item}' in docs/tools.md"


def test_foreign_boundary_trace_schema_contract() -> None:
    text = Path("docs/trace-schema.md").read_text(encoding="utf-8")
    required = [
        "boundary_start",
        "boundary_end",
        "boundary foreign",
        "function_name",
        "policy_mode",
        "input_summary",
        "output_summary",
    ]
    for item in required:
        assert item in text, f"Missing '{item}' in docs/trace-schema.md"
