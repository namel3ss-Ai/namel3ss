from pathlib import Path


LANGUAGE_CONTRACT_DOCS = [
    Path("docs/language/application-runtime.md"),
    Path("docs/language/application-data-model.md"),
    Path("docs/language/no-dependencies.md"),
    Path("docs/language/capability-packs.md"),
]


def test_language_contract_docs_exist():
    for path in LANGUAGE_CONTRACT_DOCS:
        assert path.exists()
        assert path.read_text(encoding="utf-8").strip() != ""


def test_readme_links_language_contracts():
    readme = Path("README.md").read_text(encoding="utf-8")
    assert "Language Contracts" in readme
    assert "Phase 0" not in readme
    for link in [str(path) for path in LANGUAGE_CONTRACT_DOCS]:
        assert link in readme


def test_learning_links_language_contracts():
    text = Path("docs/learning-namel3ss.md").read_text(encoding="utf-8")
    assert "Language Contracts" in text
    assert "Phase 0" not in text
    for link in [path.relative_to("docs") for path in LANGUAGE_CONTRACT_DOCS]:
        assert str(link) in text


def test_language_definition_links_language_contracts():
    text = Path("docs/ai-language-definition.md").read_text(encoding="utf-8")
    assert "Language Contracts" in text or "Related contracts" in text
    for link in [path.relative_to("docs") for path in LANGUAGE_CONTRACT_DOCS]:
        assert str(link) in text
