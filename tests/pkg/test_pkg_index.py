from pathlib import Path

from namel3ss.pkg import index as pkg_index


def test_pkg_index_loads_resources(monkeypatch):
    index_path = Path("resources/pkg_index_v1.json")
    monkeypatch.setenv(pkg_index.INDEX_PATH_ENV, str(index_path))
    entries = pkg_index.load_index()
    assert entries
    names = [entry.name for entry in entries]
    assert names == sorted(names)
    auth = pkg_index.get_entry("auth-basic", entries)
    assert auth is not None
    assert auth.trust_tier == "official"


def test_pkg_index_search_scores(monkeypatch):
    index_path = Path("resources/pkg_index_v1.json")
    monkeypatch.setenv(pkg_index.INDEX_PATH_ENV, str(index_path))
    entries = pkg_index.load_index()
    results = pkg_index.search_index("auth", entries)
    assert results
    assert results[0].entry.name == "auth-basic"
    tokens = results[0].matched_tokens
    assert "auth" in tokens
    assert results[0].score > 0


def test_pkg_index_schema_validation(monkeypatch):
    index_path = Path("resources/pkg_index_v1.json")
    data = pkg_index._read_index_data(index_path)
    errors = pkg_index.validate_index_data(data)
    assert errors == []


def test_pkg_index_contains_provider_packs(monkeypatch):
    index_path = Path("resources/pkg_index_v1.json")
    monkeypatch.setenv(pkg_index.INDEX_PATH_ENV, str(index_path))
    entries = pkg_index.load_index()
    names = {entry.name for entry in entries}
    assert {
        "huggingface-pack",
        "local-runner-pack",
        "vision-gen-pack",
        "speech-pack",
        "third-party-apis-pack",
    }.issubset(names)

    search = pkg_index.search_index("provider", entries)
    assert search
    assert any(result.entry.name == "huggingface-pack" for result in search)
