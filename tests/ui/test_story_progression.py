from __future__ import annotations

from pathlib import Path

import pytest

from namel3ss.cli.app_loader import load_program
from namel3ss.config.loader import load_config
from namel3ss.errors.base import Namel3ssError
from namel3ss.studio.api import get_ui_payload
from namel3ss.studio.session import SessionState
from namel3ss.ui.manifest import build_manifest
from namel3ss.validation_entrypoint import build_static_manifest
from tests.conftest import lower_ir_program


def test_story_simple_manifest_and_default_next():
    source = '''
spec is "1.0"

page "home":
  story "Onboarding":
    "Start"
    "Finish"
'''.lstrip()
    manifest = build_manifest(lower_ir_program(source), state={}, store=None)
    story = manifest["pages"][0]["elements"][0]
    assert story["type"] == "story"
    steps = story["steps"]
    assert [step["title"] for step in steps] == ["Start", "Finish"]
    assert steps[0]["next"]["title"] == "Finish"
    assert steps[0]["next"]["target"] == steps[1]["id"]
    assert "next" not in steps[1]


def test_story_advanced_fields_and_gate_resolution():
    source = '''
spec is "1.0"

page "home":
  story "Journey":
    step "Collect":
      text is "Collect info"
      icon is info
      image is "hero"
      tone is "informative"
      requires is "state.user.ready"
      next is "Review"
    step "Review":
      tone is "success"
'''.lstrip()
    state = {"user": {"ready": True}}
    manifest = build_manifest(lower_ir_program(source), state=state, store=None)
    steps = manifest["pages"][0]["elements"][0]["steps"]
    collect = steps[0]
    assert collect["gate"]["ready"] is True
    assert collect["gate"]["requires"] == "state.user.ready"
    assert collect["next"]["target"] == steps[1]["id"]


def test_story_duplicate_steps_error():
    source = '''
spec is "1.0"

page "home":
  story "Flow":
    "Start"
    "Start"
'''.lstrip()
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "declared more than once" in str(exc.value)


def test_story_unknown_next_suggests_fix():
    source = '''
spec is "1.0"

page "home":
  story "Flow":
    step "Start":
      next is "Miss"
    step "Finish":
      text is "Done"
    '''.lstrip()
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "unknown next step" in str(exc.value).lower()


def test_story_cycle_detection_with_path():
    source = '''
spec is "1.0"

page "home":
  story "Loop":
    step "A":
      next is "B"
    step "B":
      next is "A"
'''.lstrip()
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "cycle" in str(exc.value).lower()


def test_story_invalid_tone_and_icon_errors():
    source = '''
spec is "1.0"

page "home":
  story "Flow":
    step "Start":
      tone is "loud"
'''.lstrip()
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "tone" in str(exc.value).lower()

    source_icon = '''
spec is "1.0"

page "home":
  story "Flow":
    step "Start":
      icon is rocketship
'''.lstrip()
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source_icon)
    assert "icon" in str(exc.value).lower()


def test_story_mixed_forms_are_rejected():
    source = '''
spec is "1.0"

page "home":
  story "Flow":
    "Start"
    step "Finish":
      text is "Done"
'''.lstrip()
    with pytest.raises(Namel3ssError) as exc:
        lower_ir_program(source)
    assert "cannot mix" in str(exc.value).lower()


def test_story_manifest_determinism():
    source = '''
spec is "1.0"

page "home":
  story "Flow":
    step "One":
      next is "Two"
    step "Two":
      text is "done"
'''.lstrip()
    program = lower_ir_program(source)
    first = build_manifest(program, state={}, store=None)
    second = build_manifest(program, state={}, store=None)
    assert first == second


def test_story_within_compose_is_supported():
    source = '''
spec is "1.0"

page "home":
  compose group:
    story "Checklist":
      "One"
      "Two"
'''.lstrip()
    manifest = build_manifest(lower_ir_program(source), state={}, store=None)
    compose = manifest["pages"][0]["elements"][0]
    story = compose["children"][0]
    assert story["type"] == "story"
    assert [s["title"] for s in story["steps"]] == ["One", "Two"]


def test_story_static_manifest_matches_studio(tmp_path: Path):
    source = '''
spec is "1.0"

page "home":
  story "Flow":
    "Start"
    "Finish"
'''.lstrip()
    app_file = tmp_path / "app.ai"
    app_file.write_text(source, encoding="utf-8")
    program, _ = load_program(app_file.as_posix())
    config = load_config(app_path=app_file)
    warnings: list = []
    helper_manifest = build_static_manifest(program, config=config, state={}, store=None, warnings=warnings)
    studio_manifest = get_ui_payload(source, SessionState(), app_path=app_file.as_posix())
    assert helper_manifest.get("pages") == studio_manifest.get("pages")
    assert helper_manifest.get("ui") == studio_manifest.get("ui")
