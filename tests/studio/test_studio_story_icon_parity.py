from __future__ import annotations

from namel3ss.studio import api


def test_story_icon_manifest_and_ui_payload(tmp_path):
    source = (
        'spec is "1.0"\n\n'
        'page "home":\n'
        '  story "Setup":\n'
        '    step "Start":\n'
        "      icon is add\n"
        '      text is "Ready"\n'
    )
    app_file = tmp_path / "app.ai"
    app_file.write_text(source, encoding="utf-8")
    payload = api.get_ui_payload(source, app_path=app_file.as_posix())
    assert payload.get("ok", True) is True
    pages = payload.get("pages", [])
    story = pages[0]["elements"][0]
    step = story["steps"][0]
    assert step["icon"] == "add"
