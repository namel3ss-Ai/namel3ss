from pathlib import Path


def test_explainability_doc_exists_and_contains_core_contracts() -> None:
    path = Path("docs/explainability.md")
    assert path.exists(), "docs/explainability.md missing"
    text = path.read_text(encoding="utf-8")
    for required in [
        "Determinism and Explainability",
        "[determinism]",
        "seed",
        "redact_user_data",
        "Explain Log",
        "training_explain",
        "replay_hash",
    ]:
        assert required in text
