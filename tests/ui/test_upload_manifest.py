from __future__ import annotations

import pytest

from namel3ss.errors.base import Namel3ssError
from namel3ss.ui.manifest import build_manifest
from tests.conftest import lower_ir_program


def test_upload_manifest_defaults():
    source = '''
spec is "1.0"

page "home":
  upload receipt
'''.lstrip()
    manifest = build_manifest(lower_ir_program(source), state={}, store=None)
    upload = manifest["pages"][0]["elements"][0]
    assert upload["type"] == "upload"
    assert upload["name"] == "receipt"
    assert upload["accept"] == []
    assert upload["multiple"] is False
    assert upload["required"] is False
    assert upload["label"] == "Upload"
    assert upload["preview"] is False


def test_upload_manifest_includes_action():
    source = '''
spec is "1.0"

page "home":
  upload receipt
'''.lstrip()
    manifest = build_manifest(lower_ir_program(source), state={}, store=None)
    upload = manifest["pages"][0]["elements"][0]
    action_id = upload.get("action_id")
    assert action_id
    assert upload.get("id") == action_id
    action = manifest["actions"][action_id]
    assert action["type"] == "upload_select"
    assert action["name"] == "receipt"
    assert action["multiple"] is False
    assert action["required"] is False
    clear_action_id = upload.get("clear_action_id")
    assert isinstance(clear_action_id, str) and clear_action_id
    clear_action = manifest["actions"][clear_action_id]
    assert clear_action["type"] == "upload_clear"
    assert clear_action["name"] == "receipt"
    ingestion_actions = [
        entry for entry in manifest["actions"].values() if entry.get("type") == "ingestion_run"
    ]
    assert ingestion_actions


def test_upload_manifest_accept_and_multiple():
    source = '''
spec is "1.0"

page "home":
  upload receipt:
    accept is "pdf", "png"
    multiple is true
'''.lstrip()
    manifest = build_manifest(lower_ir_program(source), state={}, store=None)
    upload = manifest["pages"][0]["elements"][0]
    assert upload["accept"] == ["pdf", "png"]
    assert upload["multiple"] is True


def test_upload_manifest_extended_options():
    source = '''
spec is "1.0"

page "home":
  upload receipt:
    accept is "application/pdf,image/png"
    multiple is true
    required is true
    label is "Add receipt"
    preview is true
'''.lstrip()
    manifest = build_manifest(lower_ir_program(source), state={}, store=None)
    upload = manifest["pages"][0]["elements"][0]
    assert upload["accept"] == ["application/pdf", "image/png"]
    assert upload["multiple"] is True
    assert upload["required"] is True
    assert upload["label"] == "Add receipt"
    assert upload["preview"] is True
    requests = manifest.get("upload_requests")
    assert isinstance(requests, list) and requests
    assert requests[0] == {
        "name": "receipt",
        "accept": ["application/pdf", "image/png"],
        "multiple": True,
        "required": True,
        "label": "Add receipt",
        "preview": True,
    }


def test_upload_manifest_is_deterministic():
    source = '''
spec is "1.0"

page "home":
  upload receipt:
    accept is "pdf"
'''.lstrip()
    program = lower_ir_program(source)
    first = build_manifest(program, state={}, store=None)
    second = build_manifest(program, state={}, store=None)
    assert first == second


def test_upload_accept_requires_strings():
    source = '''
spec is "1.0"

page "home":
  upload receipt:
    accept is 1
'''.lstrip()
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "accept" in str(exc.value).lower()


def test_upload_accept_rejects_invalid_mime_tokens():
    source = '''
spec is "1.0"

page "home":
  upload receipt:
    accept is "application/pdf,", "image//png"
'''.lstrip()
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "accept entries" in str(exc.value).lower()


def test_upload_multiple_requires_boolean():
    source = '''
spec is "1.0"

page "home":
  upload receipt:
    multiple is "yes"
'''.lstrip()
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "multiple" in str(exc.value).lower()


def test_upload_name_must_be_unique_across_app():
    source = '''
spec is "1.0"

page "home":
  upload receipt

page "review":
  upload receipt
'''.lstrip()
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "upload name" in str(exc.value).lower()
