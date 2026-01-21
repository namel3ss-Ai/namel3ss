from pathlib import Path


def test_build_docs_contract() -> None:
    text = Path("docs/targets-and-promotion.md").read_text(encoding="utf-8")
    required = [
        ".namel3ss/build/<target>/<build_id>",
        "build.json",
        "entry.json",
        "manifest.json",
        "schema/records.json",
        "web/",
        "build_report.json",
        "n3 start",
    ]
    for item in required:
        assert item in text, f"Missing '{item}' in docs/targets-and-promotion.md"


def test_runtime_start_doc_contract() -> None:
    text = Path("docs/runtime.md").read_text(encoding="utf-8")
    required = ["n3 start", "build artifacts", "No dev overlay"]
    for item in required:
        assert item in text, f"Missing '{item}' in docs/runtime.md"
