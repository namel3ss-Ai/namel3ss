from __future__ import annotations

from pathlib import Path
import shutil

import pytest

from namel3ss.config.loader import load_config
from namel3ss.config.model import AppConfig
from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.executor import Executor
from namel3ss.runtime.packs.ops import enable_pack, verify_pack
from namel3ss.runtime.packs.trust_store import TrustedKey, add_trusted_key
from namel3ss.runtime.packs.verification import compute_pack_digest
from namel3ss.runtime.tools.resolution import resolve_tool_binding
from tests.conftest import lower_ir_program


def test_tool_pack_slugify_executes(tmp_path: Path) -> None:
    source = '''packs:
  "builtin.text"

tool "slugify text":
  implemented using python

  input:
    text is text

  output:
    text is text

spec is "1.0"

flow "demo":
  let result is slugify text:
    text is input.text
  return result
'''
    program = lower_ir_program(source)
    executor = Executor(
        program.flows[0],
        schemas={},
        tools=program.tools,
        input_data={"text": "Hello World"},
        project_root=str(tmp_path),
        pack_allowlist=getattr(program, "pack_allowlist", None),
    )
    result = executor.run()
    assert result.last_value == {"text": "hello-world"}
    tool_event = next(event for event in result.traces if event.get("type") == "tool_call")
    assert tool_event["pack_id"] == "builtin.text"
    assert tool_event["pack_name"] == "text"
    assert tool_event["pack_version"] == "stable"
    assert tool_event["protocol_version"] == 1
    assert tool_event["resolved_source"] == "builtin_pack"
    pack_checks = [
        event
        for event in result.traces
        if isinstance(event, dict)
        and event.get("type") == "capability_check"
        and event.get("capability") == "pack_permission"
    ]
    assert pack_checks
    assert any(check.get("allowed") is True for check in pack_checks)


def test_tool_pack_collision_errors(tmp_path: Path) -> None:
    source = '''packs:
  "builtin.text"

tool "slugify text":
  implemented using python

  input:
    text is text

  output:
    text is text

spec is "1.0"

flow "demo":
  let result is slugify text:
    text is input.text
  return result
'''
    (tmp_path / ".namel3ss").mkdir()
    (tmp_path / ".namel3ss" / "tools.yaml").write_text(
        'tools:\n  "slugify text":\n    kind: "python"\n    entry: "tools.custom:run"\n',
        encoding="utf-8",
    )
    program = lower_ir_program(source)
    executor = Executor(
        program.flows[0],
        schemas={},
        tools=program.tools,
        input_data={"text": "Hello World"},
        project_root=str(tmp_path),
        pack_allowlist=getattr(program, "pack_allowlist", None),
    )
    with pytest.raises(Namel3ssError) as exc:
        executor.run()
    assert "collides with a tool pack" in str(exc.value)


def test_installed_pack_executes_when_verified_and_enabled(tmp_path: Path) -> None:
    source = '''packs:
  "sample.greeter"

tool "say hello":
  implemented using python

  input:
    name is text

  output:
    message is text
    ok is boolean

spec is "1.0"

flow "demo":
  let result is say hello:
    name is input.name
  return result
'''
    app_path = tmp_path / "app.ai"
    app_path.write_text(source, encoding="utf-8")
    fixture_root = _pack_fixture("pack_good_verified")
    pack_id = "sample.greeter"
    pack_dest = tmp_path / ".namel3ss" / "packs" / pack_id
    shutil.copytree(fixture_root, pack_dest)
    manifest_text = (pack_dest / "pack.yaml").read_text(encoding="utf-8")
    tools_text = (pack_dest / "tools.yaml").read_text(encoding="utf-8")
    digest = compute_pack_digest(manifest_text, tools_text)
    add_trusted_key(tmp_path, TrustedKey(key_id="test.key", public_key=digest))
    verify_pack(tmp_path, pack_id)
    enable_pack(tmp_path, pack_id)
    config = load_config(root=tmp_path)
    program = lower_ir_program(source)
    executor = Executor(
        program.flows[0],
        schemas={},
        tools=program.tools,
        input_data={"name": "Ada"},
        project_root=str(tmp_path),
        config=config,
        pack_allowlist=getattr(program, "pack_allowlist", None),
    )
    result = executor.run()
    assert result.last_value == {"message": "Hello Ada", "ok": True}
    tool_event = next(event for event in result.traces if event.get("type") == "tool_call")
    assert tool_event["resolved_source"] == "installed_pack"
    assert tool_event["pack_id"] == pack_id
    assert tool_event["pack_version"] == "0.1.0"


def test_local_pack_resolves(tmp_path: Path) -> None:
    pack_dir = tmp_path / "packs" / "capability" / "example.greeting"
    pack_dir.mkdir(parents=True, exist_ok=True)
    (pack_dir / "pack.yaml").write_text(
        'id: "example.greeting"\n'
        'name: "Greeting Tools"\n'
        'version: "stable"\n'
        'description: "Local greeting tools."\n'
        'author: "Namel3ss"\n'
        'license: "MIT"\n'
        'tools:\n'
        '  - "compose greeting"\n',
        encoding="utf-8",
    )
    (pack_dir / "tools.yaml").write_text(
        'tools:\n'
        '  "compose greeting":\n'
        '    kind: "python"\n'
        '    entry: "tools.greet:run"\n',
        encoding="utf-8",
    )
    (pack_dir / "capabilities.yaml").write_text(
        "capabilities:\n"
        '  "compose greeting":\n'
        "    filesystem: none\n"
        "    network: none\n"
        "    env: none\n"
        "    subprocess: none\n"
        "    secrets: []\n",
        encoding="utf-8",
    )
    config = AppConfig()
    resolved = resolve_tool_binding(
        tmp_path,
        "compose greeting",
        config,
        tool_kind="python",
        line=None,
        column=None,
        allowed_packs=["example.greeting"],
    )
    assert resolved.source == "local_pack"
    assert resolved.pack_id == "example.greeting"


def _pack_fixture(name: str) -> Path:
    return Path(__file__).resolve().parents[1] / "fixtures" / "packs" / name
