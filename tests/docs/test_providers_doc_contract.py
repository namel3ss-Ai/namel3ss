from pathlib import Path


def test_providers_doc_mentions_provider_tokens_and_install_flow():
    doc = Path("docs/providers.md").read_text(encoding="utf-8")
    for token in [
        "huggingface",
        "local_runner",
        "vision_gen",
        "speech",
        "third_party_apis",
    ]:
        assert token in doc
    assert "n3 pkg add huggingface-pack" in doc
    assert "namel3ss.lock" in doc
