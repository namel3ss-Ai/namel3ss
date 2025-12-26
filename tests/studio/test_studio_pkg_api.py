from pathlib import Path

from namel3ss.pkg.index import INDEX_PATH_ENV
from namel3ss.studio import pkg_api


def test_studio_pkg_search_and_info(monkeypatch):
    index_path = Path("tests/fixtures/pkg_index.json")
    monkeypatch.setenv(INDEX_PATH_ENV, str(index_path))

    search = pkg_api.search_pkg_index_payload("demo")
    assert search["ok"] is True
    assert search["count"] == 1

    info = pkg_api.get_pkg_info_payload("demo")
    assert info["ok"] is True
    assert info["name"] == "demo"
    assert "install" in info
