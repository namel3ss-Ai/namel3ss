from __future__ import annotations

import json
from pathlib import Path

from namel3ss.cli.main import main as cli_main
from namel3ss.runtime.registry.entry import validate_registry_entry


FIXTURES_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "registry" / "bundles"
TEST_KEY = "secret"


def test_registry_add_creates_entry(tmp_path: Path, capsys, monkeypatch) -> None:
    _write_app(tmp_path)
    monkeypatch.chdir(tmp_path)
    bundle_path = FIXTURES_ROOT / "sample.nocode-0.1.0.n3pack.zip"
    assert cli_main(["registry", "add", str(bundle_path), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "ok"
    entry = payload["entry"]
    assert not validate_registry_entry(entry)
    index_path = tmp_path / ".namel3ss" / "registry" / "index.jsonl"
    assert index_path.exists()


def test_discover_ranking_and_filters(tmp_path: Path, capsys, monkeypatch) -> None:
    _write_app(tmp_path)
    monkeypatch.chdir(tmp_path)
    bundle_local = FIXTURES_ROOT / "sample.local-0.1.0.n3pack.zip"
    _add_trusted_key(tmp_path, TEST_KEY)
    assert cli_main(["registry", "add", str(bundle_local), "--json"]) == 0
    capsys.readouterr()
    bundle_service = FIXTURES_ROOT / "sample.nocode-0.1.0.n3pack.zip"
    assert cli_main(["registry", "add", str(bundle_service), "--json"]) == 0
    capsys.readouterr()

    assert cli_main(["discover", "provide tools", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["count"] == 2
    assert payload["results"][0]["pack_id"] == "sample.local"

    assert cli_main(["discover", "provide", "--risk", "low", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["count"] == 1
    assert payload["results"][0]["pack_id"] == "sample.local"

    assert cli_main(["discover", "provide", "--capability", "network", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["count"] == 1
    assert payload["results"][0]["pack_id"] == "sample.nocode"


def test_packs_add_from_registry(tmp_path: Path, capsys, monkeypatch) -> None:
    _write_app(tmp_path)
    monkeypatch.chdir(tmp_path)
    bundle_local = FIXTURES_ROOT / "sample.local-0.1.0.n3pack.zip"
    _add_trusted_key(tmp_path, TEST_KEY)
    assert cli_main(["registry", "add", str(bundle_local), "--json"]) == 0
    capsys.readouterr()
    assert cli_main(["packs", "add", "sample.local", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "ok"
    pack_path = tmp_path / ".namel3ss" / "packs" / "sample.local" / "pack.yaml"
    assert pack_path.exists()
    source_meta_path = pack_path.parent / ".n3pack_source.json"
    source_meta = json.loads(source_meta_path.read_text(encoding="utf-8"))
    assert source_meta["source_type"] == "registry"
    assert isinstance(source_meta.get("path"), str)
    assert source_meta["path"].startswith("registry:")
    unexpected = [
        item.name
        for item in tmp_path.iterdir()
        if item.is_file() and item.name not in {"app.ai", "trusted.key"}
    ]
    assert not unexpected


def test_registry_list_output_is_stable(tmp_path: Path, capsys, monkeypatch) -> None:
    _write_app(tmp_path)
    monkeypatch.chdir(tmp_path)
    bundle_service = FIXTURES_ROOT / "sample.nocode-0.1.0.n3pack.zip"
    assert cli_main(["registry", "add", str(bundle_service), "--json"]) == 0
    capsys.readouterr()
    bundle_local = FIXTURES_ROOT / "sample.local-0.1.0.n3pack.zip"
    assert cli_main(["registry", "add", str(bundle_local), "--json"]) == 0
    capsys.readouterr()

    assert cli_main(["registry", "list", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["count"] == 2
    assert [pack["pack_id"] for pack in payload["packs"]] == ["sample.local", "sample.nocode"]


def test_blocked_pack_emits_guidance(tmp_path: Path, capsys, monkeypatch) -> None:
    _write_app(tmp_path)
    monkeypatch.chdir(tmp_path)
    bundle_local = FIXTURES_ROOT / "sample.local-0.1.0.n3pack.zip"
    assert cli_main(["registry", "add", str(bundle_local), "--json"]) == 0
    capsys.readouterr()

    rc = cli_main(["packs", "add", "sample.local"])
    assert rc == 1
    captured = capsys.readouterr()
    text = (captured.out + captured.err).lower()
    assert "blocked by policy" in text


def _add_trusted_key(app_root: Path, key_text: str) -> None:
    key_file = app_root / "trusted.key"
    key_file.write_text(key_text, encoding="utf-8")
    assert cli_main(["packs", "keys", "add", "--id", "test.key", "--public-key", str(key_file), "--json"]) == 0


def _write_app(tmp_path: Path) -> None:
    (tmp_path / "app.ai").write_text('spec is "1.0"\n\nflow "demo":\n  return "ok"\n', encoding="utf-8")
