from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from namel3ss.cli.main import main as cli_main


FIXTURES_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "packs_authoring"


def test_packs_init_creates_structure(tmp_path: Path, capsys) -> None:
    pack_id = "sample.init"
    assert cli_main(["packs", "init", pack_id, "--dir", str(tmp_path), "--no-code", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    pack_path = Path(payload["path"])
    assert pack_path.exists()
    assert (pack_path / "pack.yaml").exists()
    assert (pack_path / "tools.yaml").exists()
    assert (pack_path / "intent.md").exists()
    assert (pack_path / "signature.txt").exists()
    assert not (pack_path / "tools").exists()
    rc = cli_main(["packs", "init", pack_id, "--dir", str(tmp_path)])
    assert rc == 1


def test_packs_validate_strict_modes(tmp_path: Path, capsys) -> None:
    valid_no_code = FIXTURES_ROOT / "pack_minimal_no_code"
    valid_local = FIXTURES_ROOT / "pack_python_local"
    invalid_intent = FIXTURES_ROOT / "pack_invalid_missing_intent"
    invalid_caps = FIXTURES_ROOT / "pack_invalid_missing_capabilities"

    assert cli_main(["packs", "validate", str(valid_no_code), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "ok"

    assert cli_main(["packs", "validate", str(valid_local), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "ok"

    rc = cli_main(["packs", "validate", str(invalid_intent), "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 1
    assert payload["status"] == "fail"

    rc = cli_main(["packs", "validate", str(invalid_caps), "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert payload["status"] == "warn"

    rc = cli_main(["packs", "validate", str(invalid_caps), "--strict", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 1
    assert payload["status"] == "fail"


def test_packs_bundle_is_deterministic(tmp_path: Path, capsys) -> None:
    pack_dir = FIXTURES_ROOT / "pack_python_local"
    out_dir = tmp_path / "dist"
    assert cli_main(["packs", "bundle", str(pack_dir), "--out", str(out_dir), "--json"]) == 0
    first = json.loads(capsys.readouterr().out)
    bundle_path = Path(first["bundle_path"])
    digest_one = _hash_file(bundle_path)
    assert cli_main(["packs", "bundle", str(pack_dir), "--out", str(out_dir), "--json"]) == 0
    second = json.loads(capsys.readouterr().out)
    bundle_path_two = Path(second["bundle_path"])
    digest_two = _hash_file(bundle_path_two)
    assert digest_one == digest_two


def test_packs_sign_creates_signature_and_metadata(tmp_path: Path, capsys) -> None:
    pack_dir = tmp_path / "pack"
    shutil.copytree(FIXTURES_ROOT / "pack_python_local", pack_dir)
    key_file = tmp_path / "private.key"
    key_file.write_text("secret", encoding="utf-8")
    assert cli_main(
        ["packs", "sign", str(pack_dir), "--key-id", "test.key", "--private-key", str(key_file), "--json"]
    ) == 0
    payload = json.loads(capsys.readouterr().out)
    signature_text = (pack_dir / "signature.txt").read_text(encoding="utf-8")
    assert signature_text.startswith("sha256:")
    manifest_text = (pack_dir / "pack.yaml").read_text(encoding="utf-8")
    assert f'signer_id: "{payload["signer_id"]}"' in manifest_text
    assert f'digest: "{payload["digest"]}"' in manifest_text


def test_packs_add_bundle_verify_enable(tmp_path: Path, monkeypatch, capsys) -> None:
    _write_app(tmp_path)
    pack_dir = tmp_path / "pack_source"
    shutil.copytree(FIXTURES_ROOT / "pack_python_local", pack_dir)
    key_file = tmp_path / "private.key"
    key_file.write_text("secret", encoding="utf-8")
    assert cli_main(
        ["packs", "sign", str(pack_dir), "--key-id", "test.key", "--private-key", str(key_file), "--json"]
    ) == 0
    sign_payload = json.loads(capsys.readouterr().out)
    out_dir = tmp_path / "dist"
    assert cli_main(["packs", "bundle", str(pack_dir), "--out", str(out_dir), "--json"]) == 0
    bundle_payload = json.loads(capsys.readouterr().out)
    bundle_path = bundle_payload["bundle_path"]
    monkeypatch.chdir(tmp_path)
    assert cli_main(["packs", "add", bundle_path, "--json"]) == 0
    capsys.readouterr()
    trusted_key = tmp_path / "pack.pub"
    trusted_key.write_text(sign_payload["digest"], encoding="utf-8")
    assert cli_main(
        ["packs", "keys", "add", "--id", "test.key", "--public-key", str(trusted_key), "--json"]
    ) == 0
    capsys.readouterr()
    assert cli_main(["packs", "verify", "sample.local", "--json"]) == 0
    capsys.readouterr()
    assert cli_main(["packs", "enable", "sample.local", "--json"]) == 0
    capsys.readouterr()
    assert cli_main(["packs", "status", "--json"]) == 0
    status = json.loads(capsys.readouterr().out)
    pack = next(item for item in status["packs"] if item["pack_id"] == "sample.local")
    assert pack["verified"] is True
    assert pack["enabled"] is True
    assert pack["source_info"]["source_type"] == "bundle"


def test_packs_review_json_output(capsys) -> None:
    pack_dir = FIXTURES_ROOT / "pack_minimal_no_code"
    assert cli_main(["packs", "review", str(pack_dir), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["pack_id"] == "sample.nocode"
    assert payload["tools"] == ["echo service"]
    assert "service" in payload["runners"]
    assert payload["capabilities"]["summary"]["levels"]["network"] == "outbound"


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def _write_app(tmp_path: Path) -> None:
    (tmp_path / "app.ai").write_text('flow "demo":\n  return "ok"\n', encoding="utf-8")
