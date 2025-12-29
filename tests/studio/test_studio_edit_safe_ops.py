from __future__ import annotations

from pathlib import Path

import pytest

from namel3ss.studio.api import apply_edit, get_actions_payload, get_ui_payload
from namel3ss.studio.session import SessionState


APP_SOURCE = '''
spec is "1.0"

flow "demo":
  return "ok"

page "home":
  title is "Welcome"
  text is "Hello"
  button "Run":
    calls flow "demo"
'''.lstrip()


def test_edit_title_text_and_button(tmp_path: Path) -> None:
    app_file = tmp_path / "app.ai"
    app_file.write_text(APP_SOURCE, encoding="utf-8")
    session = SessionState()

    manifest = get_ui_payload(APP_SOURCE, session)
    page = manifest["pages"][0]
    title_id = next(el["element_id"] for el in page["elements"] if el["type"] == "title")
    text_id = next(el["element_id"] for el in page["elements"] if el["type"] == "text")
    button_id = next(el["element_id"] for el in page["elements"] if el["type"] == "button")

    apply_edit(str(app_file), "set_title", {"page": "home", "element_id": title_id}, "New Title", session)
    updated = app_file.read_text(encoding="utf-8")
    assert 'title is "New Title"' in updated

    apply_edit(
        str(app_file),
        "set_text",
        {"page": "home", "element_id": text_id},
        "Updated text",
        session,
    )
    updated = app_file.read_text(encoding="utf-8")
    assert 'text is "Updated text"' in updated

    apply_edit(
        str(app_file),
        "set_button_label",
        {"page": "home", "element_id": button_id},
        "Launch",
        session,
    )
    updated = app_file.read_text(encoding="utf-8")
    assert 'button "Launch":' in updated

    actions = get_actions_payload(updated)
    assert actions["ok"] is True
    ids = [a["id"] for a in actions["actions"]]
    assert "page.home.button.launch" in ids
    assert "page.home.button.run" not in ids


def test_edit_invalid_target_does_not_write(tmp_path: Path) -> None:
    app_file = tmp_path / "app.ai"
    app_file.write_text(APP_SOURCE, encoding="utf-8")
    session = SessionState()
    original = app_file.read_text(encoding="utf-8")

    with pytest.raises(Exception):
        apply_edit(str(app_file), "set_title", {"page": "home", "element_id": "page.home.title.99"}, "X", session)

    assert app_file.read_text(encoding="utf-8") == original
