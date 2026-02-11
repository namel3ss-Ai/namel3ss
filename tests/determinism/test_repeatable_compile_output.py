from __future__ import annotations

from namel3ss.config.loader import load_config
from namel3ss.determinism import canonical_json_dumps
from namel3ss.module_loader import load_project
from namel3ss.validation_entrypoint import build_static_manifest


def test_repeat_compile_output_is_byte_identical_with_includes(tmp_path) -> None:
    root = tmp_path
    app = root / "app.ai"
    module_flow = root / "modules" / "flows.ai"
    module_record = root / "modules" / "records.ai"
    module_flow.parent.mkdir(parents=True, exist_ok=True)

    app.write_text(
        """
spec is "1.0"

capabilities:
  composition.includes

include "modules/flows.ai"
include "modules/records.ai"

flow "root_main":
  return "ok"

page "home":
  title is "Deterministic"
  button "Run":
    calls flow "helper"
""".lstrip(),
        encoding="utf-8",
    )
    module_flow.write_text(
        """
flow "helper":
  return "helper"
""".lstrip(),
        encoding="utf-8",
    )
    module_record.write_text(
        """
record "Profile":
  name string must be present
""".lstrip(),
        encoding="utf-8",
    )

    first = load_project(app)
    second = load_project(app)

    config = load_config(app_path=app)
    first_manifest = build_static_manifest(first.program, config=config, state={}, store=None, warnings=[])
    second_manifest = build_static_manifest(second.program, config=config, state={}, store=None, warnings=[])

    assert canonical_json_dumps(first_manifest, pretty=False, drop_run_keys=False) == canonical_json_dumps(
        second_manifest,
        pretty=False,
        drop_run_keys=False,
    )
    assert getattr(first.program, "composition_source_map", []) == getattr(second.program, "composition_source_map", [])
