from pathlib import Path


def test_reserved_words_doc_exists():
    assert Path("docs/language/reserved-words.md").exists()


def test_learning_links_reserved_words():
    text = Path("docs/learning-namel3ss.md").read_text(encoding="utf-8")
    assert "language/reserved-words.md" in text


def test_readme_mentions_reserved_identifiers():
    readme = Path("README.md").read_text(encoding="utf-8").lower()
    assert "reserved identifiers" in readme
    assert "reserved words" in readme
    assert "n3 reserved" in readme
