from __future__ import annotations

from pathlib import Path

from namel3ss.utils.json_tools import dumps as json_dumps


EXPORT_DIRNAME = "contract"


def write_ui_exports(
    project_root: Path,
    *,
    ui: dict,
    actions: dict,
    schema: dict,
) -> dict:
    export_dir = project_root / ".namel3ss" / "ui" / EXPORT_DIRNAME
    export_dir.mkdir(parents=True, exist_ok=True)
    ui_path = export_dir / "ui.json"
    actions_path = export_dir / "actions.json"
    schema_path = export_dir / "schema.json"
    ui_path.write_text(_stable_json(ui), encoding="utf-8")
    actions_path.write_text(_stable_json(actions), encoding="utf-8")
    schema_path.write_text(_stable_json(schema), encoding="utf-8")
    return {
        "export_dir": str(export_dir),
        "ui_path": str(ui_path),
        "actions_path": str(actions_path),
        "schema_path": str(schema_path),
    }


def _stable_json(payload: object) -> str:
    return json_dumps(payload, indent=2, sort_keys=True) + "\n"


__all__ = ["EXPORT_DIRNAME", "write_ui_exports"]
