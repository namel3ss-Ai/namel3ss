from __future__ import annotations

from pathlib import Path

from namel3ss.module_loader import load_project


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_include_composition_preserves_order_and_relative_source_map(tmp_path: Path) -> None:
    app = tmp_path / "app.ai"
    _write(
        app,
        """
spec is "1.0"

capabilities:
  composition.includes

include "modules/one.ai"
include "modules\\\\two.ai"

flow "root_main":
  return "ok"
""".lstrip(),
    )
    _write(
        tmp_path / "modules" / "one.ai",
        """
flow "include_first":
  return "one"
""".lstrip(),
    )
    _write(
        tmp_path / "modules" / "two.ai",
        """
flow "include_second":
  return "two"
""".lstrip(),
    )

    project = load_project(app)
    program = project.program

    assert getattr(program, "composed_include_paths", []) == ["modules/one.ai", "modules/two.ai"]

    include_flow_names = [flow.name for flow in program.flows if flow.name in {"include_first", "include_second"}]
    assert include_flow_names == ["include_first", "include_second"]

    source_map = getattr(program, "composition_source_map", [])
    assert source_map
    assert {entry.get("file") for entry in source_map if isinstance(entry, dict)} == {"modules/one.ai", "modules/two.ai"}
    for entry in source_map:
        if not isinstance(entry, dict):
            continue
        file_path = str(entry.get("file") or "")
        assert file_path
        assert not file_path.startswith("/")
        assert ":" not in file_path.split("/", 1)[0]
        assert ".." not in file_path.split("/")


def test_duplicate_include_is_collapsed_with_stable_warning(tmp_path: Path) -> None:
    app = tmp_path / "app.ai"
    _write(
        app,
        """
spec is "1.0"

capabilities:
  composition.includes

include "modules/one.ai"
include "modules\\\\one.ai"

flow "root_main":
  return "ok"
""".lstrip(),
    )
    _write(
        tmp_path / "modules" / "one.ai",
        """
flow "helper":
  return "one"
""".lstrip(),
    )

    project = load_project(app)
    program = project.program

    assert getattr(program, "composed_include_paths", []) == ["modules/one.ai"]
    warnings = getattr(program, "composition_include_warnings", [])
    assert len(warnings) == 1
    warning = warnings[0]
    assert warning["code"] == "composition.duplicate_include"
    assert warning["message"] == 'Warning: Duplicate include ignored: "modules/one.ai"'
    assert warning["file"] == "app.ai"

