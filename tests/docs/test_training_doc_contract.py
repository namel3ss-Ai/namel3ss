from pathlib import Path


def test_training_doc_exists_and_contains_core_contracts() -> None:
    path = Path("docs/training.md")
    assert path.exists(), "docs/training.md missing"
    text = path.read_text(encoding="utf-8")
    for required in [
        "n3 train",
        "training",
        "Determinism",
        "Data contracts",
        "model_base",
        "dataset",
        "output_name",
    ]:
        assert required in text
