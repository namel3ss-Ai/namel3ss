from pathlib import Path


def test_performance_doc_exists_and_contains_core_contracts() -> None:
    path = Path("docs/performance.md")
    assert path.exists(), "docs/performance.md missing"
    text = path.read_text(encoding="utf-8")
    for required in [
        "performance",
        "async_runtime",
        "max_concurrency",
        "cache_size",
        "enable_batching",
        "Determinism",
        "Error behaviour",
    ]:
        assert required in text
