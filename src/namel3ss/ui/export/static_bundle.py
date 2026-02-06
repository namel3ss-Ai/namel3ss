from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

from namel3ss.determinism import canonical_json_dumps
from namel3ss.resources import package_root
from namel3ss.runtime.ui_api import (
    build_ui_actions_payload,
    build_ui_manifest_payload,
    build_ui_state_payload,
)

UI_BUNDLE_VERSION = "1"
_RUNTIME_ASSET_NAMES = ("runtime.css", "runtime.js")


def write_static_ui_bundle(output_root: Path, *, contract_payload: dict, revision: str = "") -> dict:
    root = Path(output_root).resolve()
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)

    ui_export = contract_payload.get("ui") if isinstance(contract_payload.get("ui"), dict) else {}
    actions_export = contract_payload.get("actions") if isinstance(contract_payload.get("actions"), dict) else {}
    schema_export = contract_payload.get("schema") if isinstance(contract_payload.get("schema"), dict) else {}

    manifest_payload = build_ui_manifest_payload(
        {
            "ok": True,
            "pages": ui_export.get("pages", []),
            "actions": _actions_map(actions_export),
            "theme": ui_export.get("theme", {}),
        },
        revision=revision,
    )
    actions_payload = build_ui_actions_payload(
        {
            "ok": True,
            "actions": _actions_map(actions_export),
        },
        revision=revision,
    )
    state_payload = build_ui_state_payload({"ok": True, "state": {}, "revision": revision}, revision=revision)

    _write_json(root / "ui_manifest.json", manifest_payload)
    _write_json(root / "ui_actions.json", actions_payload)
    _write_json(root / "ui_state.json", state_payload)
    _write_json(root / "ui_schema.json", schema_export)

    runtime_root = package_root() / "runtime" / "web"
    _copy_text(runtime_root / "preview.html", root / "index.html")
    for name in _RUNTIME_ASSET_NAMES:
        _copy_text(runtime_root / name, root / name)

    files = _bundle_files(root)
    _write_json(
        root / "bundle_manifest.json",
        {
            "ok": True,
            "bundle_version": UI_BUNDLE_VERSION,
            "api_version": manifest_payload.get("api_version", "1"),
            "revision": revision,
            "files": files,
        },
    )

    return {
        "ok": True,
        "bundle_version": UI_BUNDLE_VERSION,
        "output_dir": str(root),
        "manifest_path": str(root / "bundle_manifest.json"),
        "files": files,
    }


def _actions_map(actions_export: dict) -> dict:
    items = actions_export.get("actions") if isinstance(actions_export, dict) else None
    result: dict[str, dict] = {}
    if not isinstance(items, list):
        return result
    for item in items:
        if not isinstance(item, dict):
            continue
        action_id = item.get("id")
        if not isinstance(action_id, str) or not action_id:
            continue
        result[action_id] = {
            "type": item.get("type"),
            "flow": item.get("flow"),
            "record": item.get("record"),
        }
    return result


def _copy_text(src: Path, dest: Path) -> None:
    text = src.read_text(encoding="utf-8")
    lines = [line.rstrip() for line in text.splitlines()]
    normalized = "\n".join(lines).strip() + "\n"
    dest.write_text(normalized, encoding="utf-8", newline="\n")


def _write_json(path: Path, payload: object) -> None:
    path.write_text(canonical_json_dumps(payload, pretty=True), encoding="utf-8", newline="\n")


def _bundle_files(root: Path) -> list[dict]:
    rows: list[dict] = []
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        rows.append({"path": rel, "sha256": digest})
    return rows


__all__ = ["UI_BUNDLE_VERSION", "write_static_ui_bundle"]
