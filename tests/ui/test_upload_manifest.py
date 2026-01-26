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


def test_upload_name_must_be_unique_in_page():
    source = '''
spec is "1.0"

page "home":
  upload receipt
  upload receipt
'''.lstrip()
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "upload name" in str(exc.value).lower()
