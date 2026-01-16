from pathlib import Path


def test_schema_evolution_doc_contract() -> None:
    text = Path("docs/identity-and-persistence.md").read_text(encoding="utf-8")
    required = [
        "Schema evolution and data contracts",
        ".namel3ss/schema/last.json",
        "build/<target>/<build_id>/schema/records.json",
        "Add a new optional field",
        "Change a field type",
        'view of "<Record>"',
        "id ascending",
    ]
    for item in required:
        assert item in text, f"Missing '{item}' in docs/identity-and-persistence.md"
