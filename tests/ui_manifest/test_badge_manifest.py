from __future__ import annotations

from namel3ss.ui.manifest import build_manifest
from tests.conftest import lower_ir_program


SOURCE = '''spec is "1.0"

page "status":
  title is "Statuses"
  badge from state.status style is success
  badge from state.secondary
'''

STATE = {
    "status": "READY",
    "secondary": "PENDING",
}


def test_badge_manifest_binds_text_and_style() -> None:
    program = lower_ir_program(SOURCE)
    manifest = build_manifest(program, state=dict(STATE), store=None)
    pages = manifest.get("pages", [])
    page = next(page for page in pages if page.get("slug") == "status")
    elements = page.get("elements", [])
    badges = [el for el in elements if el.get("type") == "badge"]
    assert [badge.get("text") for badge in badges] == ["READY", "PENDING"]
    assert [badge.get("style") for badge in badges] == ["success", "neutral"]
    assert [badge.get("source") for badge in badges] == ["state.status", "state.secondary"]
