from __future__ import annotations

from pathlib import Path
import shutil

import pytest

from namel3ss.config.loader import load_config
from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.executor import Executor
from namel3ss.runtime.packs.ops import enable_pack, verify_pack
from namel3ss.runtime.packs.trust_store import TrustedKey, add_trusted_key
from namel3ss.runtime.packs.verification import compute_pack_digest
from tests.conftest import lower_ir_program


def test_tool_pack_slugify_executes(tmp_path: Path) -> None:
    source = '''tool "slugify text":
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
    )
    result = executor.run()
    assert result.last_value == {"text": "hello-world"}
    tool_event = next(event for event in result.traces if event.get("type") == "tool_call")
    assert tool_event["pack_id"] == "builtin.text"
    assert tool_event["pack_name"] == "text"
    assert tool_event["pack_version"] == "v1"
    assert tool_event["protocol_version"] == 1
    assert tool_event["resolved_source"] == "builtin_pack"


def test_tool_pack_collision_errors(tmp_path: Path) -> None:
    source = '''tool "slugify text":
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
    )
    with pytest.raises(Namel3ssError) as exc:
        executor.run()
    assert "collides with a tool pack" in str(exc.value)


def test_installed_pack_executes_when_verified_and_enabled(tmp_path: Path) -> None:
    source = '''tool "say hello":
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
    )
    result = executor.run()
    assert result.last_value == {"message": "Hello Ada", "ok": True}
    tool_event = next(event for event in result.traces if event.get("type") == "tool_call")
    assert tool_event["resolved_source"] == "installed_pack"
    assert tool_event["pack_id"] == pack_id
    assert tool_event["pack_version"] == "0.1.0"


def _pack_fixture(name: str) -> Path:
    return Path(__file__).resolve().parents[1] / "fixtures" / "packs" / name
