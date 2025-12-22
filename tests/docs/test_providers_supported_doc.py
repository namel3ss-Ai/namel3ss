from pathlib import Path

from namel3ss.runtime.ai.providers import registry as provider_registry


def test_providers_supported_doc_lists_all_ids():
    doc_path = Path("docs/providers-supported.md")
    assert doc_path.exists(), "providers-supported.md missing"
    content = doc_path.read_text()
    for provider_id in provider_registry._FACTORIES.keys():
        assert provider_id in content
