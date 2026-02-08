from __future__ import annotations

import io
from pathlib import Path
from types import SimpleNamespace

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.backend.upload_handler import handle_upload
from namel3ss.runtime.store.memory_store import MemoryStore
from namel3ss.runtime.ui.actions import handle_action
from namel3ss.ui.manifest import build_manifest
from tests.conftest import lower_ir_program


def _ctx(tmp_path: Path, *, capabilities: tuple[str, ...] = ("uploads",)) -> SimpleNamespace:
    app_path = tmp_path / "app.ai"
    app_path.write_text('spec is "1.0"\nflow "demo":\n  return "ok"\n', encoding="utf-8")
    return SimpleNamespace(
        capabilities=capabilities,
        project_root=str(tmp_path),
        app_path=app_path.as_posix(),
    )


def _upload_metadata(tmp_path: Path, payload: bytes, *, filename: str) -> dict:
    ctx = _ctx(tmp_path)
    response = handle_upload(
        ctx,
        headers={"Content-Type": "application/octet-stream"},
        rfile=io.BytesIO(payload),
        content_length=len(payload),
        upload_name=filename,
    )
    return response["upload"]


def _upload_action_id(program) -> str:
    manifest = build_manifest(program, state={}, store=MemoryStore())
    for action_id, entry in manifest.get("actions", {}).items():
        if entry.get("type") == "upload_select":
            return action_id
    raise AssertionError("Upload select action not found in manifest")


def test_upload_selection_writes_state(tmp_path: Path) -> None:
    source = '''
spec is "1.0"

page "home":
  upload receipt
'''.lstrip()
    program = lower_ir_program(source)
    action_id = _upload_action_id(program)
    metadata = _upload_metadata(tmp_path, b"hello", filename="receipt.txt")

    state: dict = {}
    response = handle_action(
        program,
        action_id=action_id,
        payload={"upload": metadata},
        state=state,
        store=MemoryStore(),
    )

    uploads = response["state"]["uploads"]["receipt"]
    assert isinstance(uploads, dict)
    entry = uploads[metadata["checksum"]]
    assert entry["id"] == metadata["checksum"]
    assert entry["name"] == metadata["name"]
    assert entry["size"] == metadata["bytes"]
    assert entry["type"] == metadata["content_type"]
    assert entry["checksum"] == metadata["checksum"]
    assert entry["state"] == "stored"
    assert entry["preview"]["checksum"] == metadata["checksum"]


def test_upload_selection_multiple_appends(tmp_path: Path) -> None:
    source = '''
spec is "1.0"

page "home":
  upload receipt:
    multiple is true
'''.lstrip()
    program = lower_ir_program(source)
    action_id = _upload_action_id(program)
    first = _upload_metadata(tmp_path, b"first", filename="first.txt")
    second = _upload_metadata(tmp_path, b"second", filename="second.txt")

    state: dict = {}
    handle_action(
        program,
        action_id=action_id,
        payload={"upload": first},
        state=state,
        store=MemoryStore(),
    )
    response = handle_action(
        program,
        action_id=action_id,
        payload={"upload": second},
        state=state,
        store=MemoryStore(),
    )

    uploads = response["state"]["uploads"]["receipt"]
    assert isinstance(uploads, dict)
    assert list(uploads.keys()) == [first["checksum"], second["checksum"]]


def test_upload_selection_single_replaces(tmp_path: Path) -> None:
    source = '''
spec is "1.0"

page "home":
  upload receipt
'''.lstrip()
    program = lower_ir_program(source)
    action_id = _upload_action_id(program)
    first = _upload_metadata(tmp_path, b"first", filename="first.txt")
    second = _upload_metadata(tmp_path, b"second", filename="second.txt")

    state: dict = {}
    handle_action(
        program,
        action_id=action_id,
        payload={"upload": first},
        state=state,
        store=MemoryStore(),
    )
    response = handle_action(
        program,
        action_id=action_id,
        payload={"upload": second},
        state=state,
        store=MemoryStore(),
    )

    uploads = response["state"]["uploads"]["receipt"]
    assert isinstance(uploads, dict)
    assert list(uploads.keys()) == [second["checksum"]]
    entry = uploads[second["checksum"]]
    assert entry["id"] == second["checksum"]
    assert entry["name"] == second["name"]
    assert entry["size"] == second["bytes"]
    assert entry["type"] == second["content_type"]
    assert entry["checksum"] == second["checksum"]
    assert entry["state"] == "stored"
    assert entry["preview"]["checksum"] == second["checksum"]


def test_upload_selection_requires_metadata() -> None:
    source = '''
spec is "1.0"

page "home":
  upload receipt
'''.lstrip()
    program = lower_ir_program(source)
    action_id = _upload_action_id(program)
    with pytest.raises(Namel3ssError) as exc:
        handle_action(
            program,
            action_id=action_id,
            payload={"upload": "nope"},
            state={},
            store=MemoryStore(),
        )
    assert "upload selection" in str(exc.value).lower()


def test_upload_clear_action_removes_entry(tmp_path: Path) -> None:
    source = '''
spec is "1.0"

page "home":
  upload receipt:
    multiple is true
'''.lstrip()
    program = lower_ir_program(source)
    manifest = build_manifest(program, state={}, store=MemoryStore())
    action_id = next(
        action_id
        for action_id, entry in manifest.get("actions", {}).items()
        if entry.get("type") == "upload_select"
    )
    clear_id = next(
        action_id
        for action_id, entry in manifest.get("actions", {}).items()
        if entry.get("type") == "upload_clear"
    )
    first = _upload_metadata(tmp_path, b"first", filename="first.txt")
    second = _upload_metadata(tmp_path, b"second", filename="second.txt")
    state: dict = {}
    handle_action(
        program,
        action_id=action_id,
        payload={"upload": first},
        state=state,
        store=MemoryStore(),
    )
    handle_action(
        program,
        action_id=action_id,
        payload={"upload": second},
        state=state,
        store=MemoryStore(),
    )
    response = handle_action(
        program,
        action_id=clear_id,
        payload={"upload_id": first["checksum"]},
        state=state,
        store=MemoryStore(),
    )
    uploads = response["state"]["uploads"]["receipt"]
    assert list(uploads.keys()) == [second["checksum"]]


def test_required_uploads_gate_flow_execution(tmp_path: Path) -> None:
    source = '''
spec is "1.0"

flow "submit":
  let files is state.uploads.receipt
  return "ok"

page "home":
  upload receipt:
    required is true
  button "Submit":
    calls flow "submit"
'''.lstrip()
    program = lower_ir_program(source)
    manifest = build_manifest(program, state={}, store=MemoryStore())
    action_id = next(
        action_id
        for action_id, entry in manifest.get("actions", {}).items()
        if entry.get("type") == "call_flow"
    )
    with pytest.raises(Namel3ssError) as exc:
        handle_action(
            program,
            action_id=action_id,
            payload={},
            state={},
            store=MemoryStore(),
        )
    assert "required upload selection is missing" in str(exc.value).lower()

    metadata = _upload_metadata(tmp_path, b"ok", filename="receipt.txt")
    state = {"uploads": {"receipt": [metadata]}}
    response = handle_action(
        program,
        action_id=action_id,
        payload={},
        state=state,
        store=MemoryStore(),
    )
    assert response.get("ok") is True
