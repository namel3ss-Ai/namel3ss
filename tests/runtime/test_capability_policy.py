from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from namel3ss.cli.packs_enable_mode import run_packs_enable
from namel3ss.config.model import AppConfig
from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.executor import Executor
from namel3ss.runtime.packs.layout import pack_verification_path
from namel3ss.runtime.packs.manifest import parse_pack_manifest
from namel3ss.runtime.packs.verification import compute_pack_digest
from tests.conftest import lower_ir_program


def test_policy_downgrade_enforced_at_runtime(tmp_path: Path) -> None:
    policy_path = tmp_path / ".namel3ss" / "trust" / "policy.toml"
    policy_path.parent.mkdir(parents=True, exist_ok=True)
    policy_path.write_text('allowed_capabilities = { network = "none" }\n', encoding="utf-8")

    source = '''tool "get json from web":
  implemented using python

  input:
    url is text

  output:
    status is number
    headers is json
    data is json

spec is "1.0"

flow "demo":
  let response is get json from web:
    url is "https://example.com/data"
  return response
'''
    program = lower_ir_program(source)
    executor = Executor(
        program.flows[0],
        schemas={},
        tools=program.tools,
        input_data={},
        config=AppConfig(),
        project_root=str(tmp_path),
    )
    with pytest.raises(Namel3ssError):
        executor.run()
    checks = [event for event in executor.traces if isinstance(event, dict) and event.get("type") == "capability_check"]
    assert any(event.get("guarantee_source") == "policy" for event in checks)


def test_policy_blocks_pack_enable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    app_path = tmp_path / "app.ai"
    app_path.write_text('spec is "1.0"\n\nflow "demo":\n  return "ok"\n', encoding="utf-8")
    policy_path = tmp_path / ".namel3ss" / "trust" / "policy.toml"
    policy_path.parent.mkdir(parents=True, exist_ok=True)
    policy_path.write_text('allowed_capabilities = { network = "none" }\n', encoding="utf-8")

    fixture_root = Path(__file__).resolve().parents[1] / "fixtures" / "packs_authoring" / "pack_minimal_no_code"
    manifest = parse_pack_manifest(fixture_root / "pack.yaml")
    pack_dest = tmp_path / ".namel3ss" / "packs" / manifest.pack_id
    shutil.copytree(fixture_root, pack_dest)

    manifest_text = (pack_dest / "pack.yaml").read_text(encoding="utf-8")
    tools_text = (pack_dest / "tools.yaml").read_text(encoding="utf-8")
    digest = compute_pack_digest(manifest_text, tools_text)
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

    monkeypatch.chdir(tmp_path)
    with pytest.raises(Namel3ssError) as exc:
        run_packs_enable([manifest.pack_id], json_mode=True)
    assert "blocked by policy" in str(exc.value).lower()
