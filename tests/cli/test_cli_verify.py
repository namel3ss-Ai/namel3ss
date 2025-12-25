import json
import shutil
from pathlib import Path

from namel3ss.cli.main import main
from namel3ss.config.model import ToolPacksConfig
from namel3ss.pkg.lockfile import LOCKFILE_FILENAME
from namel3ss.runtime.packs.config import write_pack_config
from namel3ss.runtime.packs.layout import pack_verification_path
from namel3ss.runtime.packs.manifest import parse_pack_manifest
from namel3ss.runtime.packs.verification import compute_pack_digest


FIXTURES_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "packs_authoring"


BASE_SOURCE = '''record "Item":
  field "name" is text

flow "demo":
  return "ok"
'''


MUTATING_SOURCE = '''record "Item":
  field "name" is text

flow "seed":
  save Item
'''


def _write_app(tmp_path, source):
    path = tmp_path / "app.ai"
    path.write_text(source, encoding="utf-8")


def _write_lock(tmp_path):
    lock_path = tmp_path / LOCKFILE_FILENAME
    lock_path.write_text('{"lockfile_version":1,"roots":[],"packages":[]}', encoding="utf-8")


def _prepare_packages(tmp_path):
    (tmp_path / "packages").mkdir()


def _write_tools_binding(tmp_path: Path, tool_name: str) -> None:
    tools_dir = tmp_path / ".namel3ss"
    tools_dir.mkdir(exist_ok=True)
    (tools_dir / "tools.yaml").write_text(
        "tools:\n"
        f'  "{tool_name}":\n'
        '    kind: "python"\n'
        '    entry: "tools.danger:run"\n'
        "    sandbox: true\n",
        encoding="utf-8",
    )


def test_verify_ok_json(tmp_path, capsys, monkeypatch):
    _write_app(tmp_path, BASE_SOURCE)
    _write_lock(tmp_path)
    _prepare_packages(tmp_path)
    monkeypatch.chdir(tmp_path)
    main(["pack", "--target", "local"])
    capsys.readouterr()
    code = main(["verify", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["status"] == "ok"
    assert payload["schema_version"] == 1


def test_verify_prod_fails_on_public_mutation(tmp_path, capsys, monkeypatch):
    _write_app(tmp_path, MUTATING_SOURCE)
    _write_lock(tmp_path)
    _prepare_packages(tmp_path)
    monkeypatch.chdir(tmp_path)
    main(["pack", "--target", "local"])
    capsys.readouterr()
    code = main(["verify", "--prod", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 1
    assert payload["status"] == "fail"


def test_verify_prod_fails_on_missing_pack_capabilities(tmp_path, capsys, monkeypatch):
    _write_app(tmp_path, BASE_SOURCE)
    _write_lock(tmp_path)
    _prepare_packages(tmp_path)

    fixture_root = FIXTURES_ROOT / "pack_python_local"
    manifest = parse_pack_manifest(fixture_root / "pack.yaml")
    pack_dest = tmp_path / ".namel3ss" / "packs" / manifest.pack_id
    shutil.copytree(fixture_root, pack_dest)

    manifest_text = (pack_dest / "pack.yaml").read_text(encoding="utf-8")
    digest = compute_pack_digest(manifest_text, None)
    verification = {
        "pack_id": manifest.pack_id,
        "version": manifest.version,
        "digest": digest,
        "verified": True,
        "key_id": "test.key",
        "verified_at": "2024-01-01T00:00:00Z",
    }
    pack_verification_path(pack_dest).write_text(
        json.dumps(verification, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    write_pack_config(tmp_path, ToolPacksConfig(enabled_packs=[manifest.pack_id], disabled_packs=[], pinned_tools={}))
    monkeypatch.chdir(tmp_path)
    main(["pack", "--target", "local"])
    capsys.readouterr()
    code = main(["verify", "--prod", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 1
    assert payload["status"] == "fail"
    check = next(item for item in payload["checks"] if item["id"] == "pack_capabilities")
    assert manifest.pack_id in check.get("details", {}).get("missing_capabilities", [])


def test_verify_prod_fails_on_unsafe_override(tmp_path, capsys, monkeypatch):
    source = '''tool "danger tool":
  implemented using python

  input:
    payload is json

  output:
    ok is boolean

flow "demo":
  return "ok"
'''
    _write_app(tmp_path, source)
    _write_tools_binding(tmp_path, "danger tool")
    (tmp_path / "namel3ss.toml").write_text(
        "[capability_overrides]\n"
        "\"danger tool\" = { allow_unsafe_execution = true }\n",
        encoding="utf-8",
    )
    _write_lock(tmp_path)
    _prepare_packages(tmp_path)
    monkeypatch.chdir(tmp_path)
    main(["pack", "--target", "local"])
    capsys.readouterr()
    code = main(["verify", "--prod", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 1
    assert payload["status"] == "fail"
    check = next(item for item in payload["checks"] if item["id"] == "tool_guarantees")
    assert "danger tool" in check.get("details", {}).get("unsafe_overrides", [])


def test_verify_prod_allows_unsafe_with_flag(tmp_path, capsys, monkeypatch):
    source = '''tool "danger tool":
  implemented using python

  input:
    payload is json

  output:
    ok is boolean

flow "demo":
  return "ok"
'''
    _write_app(tmp_path, source)
    _write_tools_binding(tmp_path, "danger tool")
    (tmp_path / "namel3ss.toml").write_text(
        "[capability_overrides]\n"
        "\"danger tool\" = { allow_unsafe_execution = true }\n",
        encoding="utf-8",
    )
    _write_lock(tmp_path)
    _prepare_packages(tmp_path)
    monkeypatch.chdir(tmp_path)
    main(["pack", "--target", "local"])
    capsys.readouterr()
    code = main(["verify", "--prod", "--allow-unsafe", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["status"] == "ok"
