import json
from pathlib import Path

from namel3ss.cli.main import main


def _write_project(root: Path) -> None:
    (root / "packages").mkdir()
    (root / "namel3ss.lock.json").write_text('{"lockfile_version":1,"roots":[],"packages":[]}', encoding="utf-8")
    (root / "app.ai").write_text(
        'identity "User":\n'
        '  field "role" is text must be present\n\n'
        'use "inventory" as inv\n\n'
        'page "home": requires identity.role is "admin"\n'
        '  title is "Demo"\n'
        '  button "Seed":\n'
        '    calls flow "inv.seed"\n',
        encoding="utf-8",
    )
    module_dir = root / "modules" / "inventory"
    module_dir.mkdir(parents=True)
    (module_dir / "capsule.ai").write_text(
        'capsule "inventory":\n  exports:\n    flow "seed"\n',
        encoding="utf-8",
    )
    (module_dir / "logic.ai").write_text(
        'flow "seed": requires identity.role is "admin"\n'
        '  return "ok"\n',
        encoding="utf-8",
    )
    proof_dir = root / ".namel3ss" / "proofs"
    proof_dir.mkdir(parents=True)
    (root / ".namel3ss" / "active_proof.json").write_text(
        json.dumps({"proof_id": "proof-123", "target": "local", "build_id": None}),
        encoding="utf-8",
    )
    (root / ".namel3ss" / "verify.json").write_text(
        json.dumps({"status": "ok", "checks": []}),
        encoding="utf-8",
    )


def test_cli_why_human_output(tmp_path: Path, monkeypatch, capsys) -> None:
    _write_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    code = main(["why"])
    out = capsys.readouterr().out.strip().splitlines()
    assert code == 0
    assert out[0].startswith("- Why this app")
    assert any("Proof: proof-123" in line for line in out)
    assert any("Verify: ok" in line for line in out)


def test_cli_why_json_output(tmp_path: Path, monkeypatch, capsys) -> None:
    _write_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    code = main(["why", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["schema_version"] == 1
    assert payload["verify_status"] == "ok"
    assert payload["proof_id"] == "proof-123"
