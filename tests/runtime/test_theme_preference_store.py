import json
from pathlib import Path

from namel3ss.runtime.executor.api import execute_program_flow
from namel3ss.runtime.preferences.factory import app_pref_key, preference_store_for_app
from tests.conftest import lower_ir_program


def test_preference_load_and_save(tmp_path: Path):
    app_path = tmp_path / "app.ai"
    app_path.write_text('app:\n  theme is "system"\n  theme_preference:\n    allow_override is true\n    persist is "file"\nspec is "1.0"\n\nflow "demo":\n  set theme to "dark"\n', encoding="utf-8")
    program_ir = lower_ir_program(app_path.read_text(encoding="utf-8"))
    store = preference_store_for_app(str(app_path), program_ir.theme_preference.get("persist"))
    key = app_pref_key(str(app_path))
    # initial save via execution
    result = execute_program_flow(program_ir, "demo", state={}, input={}, preference_store=store, preference_key=key)
    assert result.runtime_theme == "dark"
    data = json.loads((tmp_path / ".namel3ss" / "preferences.json").read_text(encoding="utf-8"))
    assert data["themes"][key] == "dark"
    # load on next run
    result2 = execute_program_flow(
        program_ir,
        "demo",
        state={},
        input={},
        runtime_theme=None,
        preference_store=store,
        preference_key=key,
    )
    assert result2.runtime_theme == "dark"
