from __future__ import annotations

import json
from pathlib import Path

import pytest

from namel3ss.config.model import AppConfig
from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.executor import Executor
from namel3ss.runtime.packs.verification import compute_pack_digest
from namel3ss.runtime.tools.resolution import resolve_tool_binding
from tests.conftest import lower_ir_program


def test_unbound_tool_error_mentions_tool_name(tmp_path: Path) -> None:
    config = AppConfig()
    with pytest.raises(Namel3ssError) as exc:
        resolve_tool_binding(tmp_path, "echo payload", config, tool_kind="python", line=None, column=None)
    message = str(exc.value)
    assert 'Tool "echo payload" is not bound to a python entry.' in message


def test_pack_collision_error_lists_pack_ids(tmp_path: Path) -> None:
    pack_root = tmp_path / ".namel3ss" / "packs"
    _write_pack(pack_root, pack_id="collision.a", tool_name="pack echo", entry="tools.echo:run", verified=True)
    _write_pack(pack_root, pack_id="collision.b", tool_name="pack echo", entry="tools.echo:run", verified=True)
    config = AppConfig()
    config.tool_packs.enabled_packs = ["collision.a", "collision.b"]

    with pytest.raises(Namel3ssError) as exc:
        resolve_tool_binding(tmp_path, "pack echo", config, tool_kind="python", line=None, column=None)

    message = str(exc.value)
    assert 'Tool "pack echo" is provided by multiple packs.' in message
    assert "collision.a" in message
    assert "collision.b" in message


def test_installed_pack_import_error_includes_reason(tmp_path: Path) -> None:
    pack_root = tmp_path / ".namel3ss" / "packs"
    _write_pack(pack_root, pack_id="broken.pack", tool_name="pack echo", entry="tools.missing:run", verified=True)
    config = AppConfig()
    config.tool_packs.enabled_packs = ["broken.pack"]

    source = '''tool "pack echo":
  implemented using python

  input:
    payload is json

  output:
    result is json

spec is "1.0"

flow "demo":
  let result is pack echo:
    payload is input.payload
  return result
'''
    program = lower_ir_program(source)
    flow = program.flows[0]
    executor = Executor(
        flow,
        schemas={},
        tools=program.tools,
        input_data={"payload": {"ok": True}},
        project_root=str(tmp_path),
        config=config,
    )
    with pytest.raises(Namel3ssError) as exc:
        executor.run()
    message = str(exc.value)
    assert "ModuleNotFoundError" in message
    assert "No module named" in message


def _write_pack(root: Path, *, pack_id: str, tool_name: str, entry: str, verified: bool) -> Path:
    pack_dir = root / pack_id
    pack_dir.mkdir(parents=True, exist_ok=True)
    manifest_text = (
        f'id: "{pack_id}"\n'
        f'name: "{pack_id}"\n'
        'version: "1.0.0"\n'
        'description: "Spec fixture"\n'
        'author: "Namel3ss"\n'
        'license: "MIT"\n'
        'tools:\n'
        f'  - "{tool_name}"\n'
    )
    tools_text = (
        'tools:\n'
        f'  "{tool_name}":\n'
        '    kind: "python"\n'
        f'    entry: "{entry}"\n'
    )
    (pack_dir / "pack.yaml").write_text(manifest_text, encoding="utf-8")
    (pack_dir / "tools.yaml").write_text(tools_text, encoding="utf-8")
    if verified:
        digest = compute_pack_digest(manifest_text, tools_text)
        payload = {
            "digest": digest,
            "key_id": "test",
            "pack_id": pack_id,
            "verified": True,
            "verified_at": "2024-01-01T00:00:00+00:00",
            "version": "1.0.0",
        }
        (pack_dir / "verification.json").write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    return pack_dir
