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


SPEC_FAILURES = Path(__file__).resolve().parents[2] / "spec" / "failures"


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

    source = '''packs:
  "broken.pack"

tool "pack echo":
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
        pack_allowlist=getattr(program, "pack_allowlist", None),
    )
    with pytest.raises(Namel3ssError) as exc:
        executor.run()
    message = str(exc.value)
    assert "ModuleNotFoundError" in message
    assert "No module named" in message


def test_pack_collision_trace_classification(tmp_path: Path) -> None:
    pack_root = tmp_path / ".namel3ss" / "packs"
    _write_pack(pack_root, pack_id="collision.a", tool_name="pack echo", entry="tools.echo:run", verified=True)
    _write_pack(pack_root, pack_id="collision.b", tool_name="pack echo", entry="tools.echo:run", verified=True)
    config = AppConfig()
    config.tool_packs.enabled_packs = ["collision.a", "collision.b"]

    source = _tool_source("pack echo", packs=["collision.a", "collision.b"])
    program = lower_ir_program(source)
    executor = Executor(
        program.flows[0],
        schemas={},
        tools=program.tools,
        input_data={"payload": {"ok": True}},
        project_root=str(tmp_path),
        config=config,
        pack_allowlist=getattr(program, "pack_allowlist", None),
    )
    with pytest.raises(Namel3ssError) as exc:
        executor.run()
    _assert_guidance(str(exc.value), _read_expected("packs/collision/app.json"))
    trace = _tool_trace(executor, "pack echo")
    assert trace["decision"] == "error"
    assert trace["reason"] == "pack_collision"
    assert trace["result"] == "error"


def test_unverified_pack_trace_blocked(tmp_path: Path) -> None:
    pack_root = tmp_path / ".namel3ss" / "packs"
    _write_pack(pack_root, pack_id="enabled.pack", tool_name="pack echo", entry="tools.echo:run", verified=False)
    config = AppConfig()
    config.tool_packs.enabled_packs = ["enabled.pack"]

    source = _tool_source("pack echo", packs=["enabled.pack"])
    program = lower_ir_program(source)
    executor = Executor(
        program.flows[0],
        schemas={},
        tools=program.tools,
        input_data={"payload": {"ok": True}},
        project_root=str(tmp_path),
        config=config,
        pack_allowlist=getattr(program, "pack_allowlist", None),
    )
    with pytest.raises(Namel3ssError) as exc:
        executor.run()
    _assert_guidance(str(exc.value), _read_expected("packs/enabled_unverified_pack/app.json"))
    trace = _tool_trace(executor, "pack echo")
    assert trace["decision"] == "blocked"
    assert trace["reason"] == "pack_unavailable_or_unverified"
    assert trace["result"] == "blocked"


def test_pack_not_declared_trace_blocked(tmp_path: Path) -> None:
    pack_root = tmp_path / ".namel3ss" / "packs"
    _write_pack(pack_root, pack_id="declared.pack", tool_name="pack echo", entry="tools.echo:run", verified=True)
    config = AppConfig()
    config.tool_packs.enabled_packs = ["declared.pack"]

    source = '''packs:
  "builtin.text"

tool "pack echo":
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
    executor = Executor(
        program.flows[0],
        schemas={},
        tools=program.tools,
        input_data={"payload": {"ok": True}},
        project_root=str(tmp_path),
        config=config,
        pack_allowlist=getattr(program, "pack_allowlist", None),
    )
    with pytest.raises(Namel3ssError) as exc:
        executor.run()
    print("pack_policy_denied_error", str(exc.value))
    print("pack_policy_denied_traces", executor.ctx.traces)
    trace = _tool_trace(executor, "pack echo")
    assert trace["decision"] == "blocked"
    assert trace["reason"] == "pack_not_declared"
    checks = _pack_permission_checks(executor)
    assert any(
        check.get("allowed") is False and check.get("reason") == "pack_not_declared" for check in checks
    )


def test_builtin_pack_requires_declaration(tmp_path: Path) -> None:
    source = _tool_source("slugify text")
    program = lower_ir_program(source)
    executor = Executor(
        program.flows[0],
        schemas={},
        tools=program.tools,
        input_data={"payload": {"ok": True}},
        project_root=str(tmp_path),
        config=AppConfig(),
        pack_allowlist=getattr(program, "pack_allowlist", None),
    )
    with pytest.raises(Namel3ssError):
        executor.run()
    trace = _tool_trace(executor, "slugify text")
    assert trace["decision"] == "blocked"
    assert trace["reason"] == "pack_not_declared"
    checks = _pack_permission_checks(executor)
    assert any(
        check.get("allowed") is False and check.get("reason") == "pack_not_declared" for check in checks
    )


def test_pack_policy_denied_trace_blocked(tmp_path: Path) -> None:
    pack_root = tmp_path / ".namel3ss" / "packs"
    pack_dir = _write_pack(
        pack_root,
        pack_id="restricted.pack",
        tool_name="pack echo",
        entry="tools.echo:run",
        verified=True,
        capabilities_text=(
            "capabilities:\\n"
            '  "pack echo":\\n'
            "    filesystem: none\\n"
            "    network: outbound\\n"
            "    env: none\\n"
            "    subprocess: none\\n"
            "    secrets: []\\n"
        ),
    )
    policy_dir = tmp_path / ".namel3ss" / "trust"
    policy_dir.mkdir(parents=True, exist_ok=True)
    (policy_dir / "policy.toml").write_text(
        'allowed_capabilities = { network = "none", filesystem = "none", env = "none", subprocess = "none" }\\n',
        encoding="utf-8",
    )
    config = AppConfig()
    config.tool_packs.enabled_packs = ["restricted.pack"]

    source = '''packs:
  "restricted.pack"

tool "pack echo":
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
    executor = Executor(
        program.flows[0],
        schemas={},
        tools=program.tools,
        input_data={"payload": {"ok": True}},
        project_root=str(tmp_path),
        config=config,
        pack_allowlist=getattr(program, "pack_allowlist", None),
    )
    with pytest.raises(Namel3ssError):
        executor.run()
    trace = _tool_trace(executor, "pack echo")
    assert trace["decision"] == "blocked"
    assert trace["reason"] == "pack_permission_denied"
    checks = _pack_permission_checks(executor)
    assert any(check.get("allowed") is False and check.get("reason") == "policy_denied" for check in checks)


def test_unknown_runner_trace_classification(tmp_path: Path) -> None:
    tools_dir = tmp_path / ".namel3ss"
    tools_dir.mkdir(parents=True, exist_ok=True)
    (tools_dir / "tools.yaml").write_text(
        'tools:\n'
        '  "runner echo":\n'
        '    kind: "python"\n'
        '    entry: "tools.echo:run"\n'
        '    runner: "bogus"\n',
        encoding="utf-8",
    )
    source = _tool_source("runner echo")
    program = lower_ir_program(source)
    executor = Executor(
        program.flows[0],
        schemas={},
        tools=program.tools,
        input_data={"payload": {"runner": "bogus"}},
        project_root=str(tmp_path),
    )
    with pytest.raises(Namel3ssError) as exc:
        executor.run()
    _assert_guidance(str(exc.value), _read_expected("runners/unknown_runner/app.json"))
    trace = _tool_trace(executor, "runner echo")
    assert trace["decision"] == "error"
    assert trace["reason"] == "unknown_runner"
    assert trace["result"] == "error"


def test_missing_binding_trace_classification(tmp_path: Path) -> None:
    source = _tool_source("unbound")
    program = lower_ir_program(source)
    executor = Executor(
        program.flows[0],
        schemas={},
        tools=program.tools,
        input_data={"payload": {"ok": True}},
        project_root=str(tmp_path),
    )
    with pytest.raises(Namel3ssError) as exc:
        executor.run()
    _assert_guidance(str(exc.value), _read_expected("tools/missing_binding/app.json"))
    trace = _tool_trace(executor, "unbound")
    assert trace["decision"] == "error"
    assert trace["reason"] == "missing_binding"
    assert trace["result"] == "error"


def _tool_source(tool_name: str, *, packs: list[str] | None = None) -> str:
    packs_block = ""
    if packs:
        entries = "\n".join(f'  "{pack_id}"' for pack_id in packs)
        packs_block = f"packs:\n{entries}\n\n"
    return f'''{packs_block}tool "{tool_name}":
  implemented using python

  input:
    payload is json

  output:
    result is json

spec is "1.0"

flow "demo":
  let output is {tool_name}:
    payload is input.payload
  return output
'''


def _tool_trace(executor: Executor, tool_name: str) -> dict:
    for event in executor.ctx.traces:
        if not isinstance(event, dict):
            continue
        if event.get("type") != "tool_call":
            continue
        if event.get("tool_name") == tool_name or event.get("tool") == tool_name:
            return event
    raise AssertionError(f"Missing tool_call trace for {tool_name}")


def _pack_permission_checks(executor: Executor) -> list[dict]:
    checks: list[dict] = []
    for event in executor.ctx.traces:
        if not isinstance(event, dict):
            continue
        if event.get("type") != "capability_check":
            continue
        if event.get("capability") == "pack_permission":
            checks.append(event)
    if not checks:
        raise AssertionError("Missing pack_permission capability_check trace")
    return checks


def _read_expected(relative: str) -> dict:
    path = SPEC_FAILURES / relative
    return json.loads(path.read_text(encoding="utf-8"))


def _assert_guidance(message: str, expected: dict) -> None:
    what = expected.get("what")
    if what:
        assert (
            f"error: {what}" in message
            or f"- {what}" in message
            or f"What happened: {what}" in message
        )
    why = expected.get("why")
    if why:
        assert f"- {why}" in message or f"Why: {why}" in message
    fix = expected.get("fix")
    if fix:
        assert f"- {fix}" in message or f"Fix: {fix}" in message


def _write_pack(
    root: Path,
    *,
    pack_id: str,
    tool_name: str,
    entry: str,
    verified: bool,
    capabilities_text: str | None = None,
) -> Path:
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
    if capabilities_text:
        (pack_dir / "capabilities.yaml").write_text(capabilities_text, encoding="utf-8")
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
