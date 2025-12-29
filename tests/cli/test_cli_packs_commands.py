from __future__ import annotations

import json
from pathlib import Path

from namel3ss.cli.main import main as cli_main
from namel3ss.runtime.packs.verification import compute_pack_digest


def test_packs_add_status_remove(tmp_path: Path, monkeypatch, capsys) -> None:
    _write_app(tmp_path)
    pack_src = _fixture_path("pack_good_unverified")
    monkeypatch.chdir(tmp_path)
    assert cli_main(["packs", "add", str(pack_src), "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["pack_id"] == "sample.unverified"
    assert cli_main(["packs", "status", "--json"]) == 0
    status = json.loads(capsys.readouterr().out)
    ids = [pack["pack_id"] for pack in status["packs"]]
    assert "sample.unverified" in ids
    assert cli_main(["packs", "remove", "sample.unverified", "--yes", "--json"]) == 0
    removed = json.loads(capsys.readouterr().out)
    assert removed["pack_id"] == "sample.unverified"
    assert (tmp_path / ".namel3ss" / "packs" / "sample.unverified").exists() is False


def test_packs_enable_requires_verification(tmp_path: Path, monkeypatch, capsys) -> None:
    _write_app(tmp_path)
    pack_src = _fixture_path("pack_good_unverified")
    monkeypatch.chdir(tmp_path)
    assert cli_main(["packs", "add", str(pack_src), "--json"]) == 0
    capsys.readouterr()
    rc = cli_main(["packs", "enable", "sample.unverified"])
    assert rc == 1
    captured = capsys.readouterr()
    text = captured.out + captured.err
    assert "verify" in text.lower()


def test_packs_verify_and_enable(tmp_path: Path, monkeypatch, capsys) -> None:
    _write_app(tmp_path)
    pack_src = _fixture_path("pack_good_verified")
    monkeypatch.chdir(tmp_path)
    assert cli_main(["packs", "add", str(pack_src), "--json"]) == 0
    capsys.readouterr()
    digest = compute_pack_digest(
        (pack_src / "pack.yaml").read_text(encoding="utf-8"),
        (pack_src / "tools.yaml").read_text(encoding="utf-8"),
    )
    key_file = tmp_path / "pack.key"
    key_file.write_text(digest, encoding="utf-8")
    assert cli_main(["packs", "keys", "add", "--id", "test.key", "--public-key", str(key_file), "--json"]) == 0
    capsys.readouterr()
    assert cli_main(["packs", "verify", "sample.greeter", "--json"]) == 0
    capsys.readouterr()
    assert cli_main(["packs", "enable", "sample.greeter", "--json"]) == 0
    capsys.readouterr()
    assert cli_main(["packs", "status", "--json"]) == 0
    status = json.loads(capsys.readouterr().out)
    pack = next(item for item in status["packs"] if item["pack_id"] == "sample.greeter")
    assert pack["verified"] is True
    assert pack["enabled"] is True


def _write_app(tmp_path: Path) -> None:
    (tmp_path / "app.ai").write_text('spec is "1.0"\n\nflow "demo":\n  return "ok"\n', encoding="utf-8")


def _fixture_path(name: str) -> Path:
    return Path(__file__).resolve().parents[1] / "fixtures" / "packs" / name
