from __future__ import annotations

from namel3ss.parser.core import parse
from namel3ss.ir.nodes import lower_program
from namel3ss.ui.manifest import build_manifest
from namel3ss.runtime.store.memory_store import MemoryStore


def test_manifest_has_schema_version():
    source = 'record "User":\n  field "email" is text must be present\npage "home":\n  title is "Hi"\n'
    ir = lower_program(parse(source))
    manifest = build_manifest(ir, state={}, store=MemoryStore())
    assert manifest["theme"]["schema_version"] == "1"
