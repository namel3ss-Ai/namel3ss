from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from typing import Dict

from namel3ss.cli.targets_store import BUILD_META_FILENAME, build_dir, write_json
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.resources import package_root, studio_web_root
from namel3ss.schema.evolution import build_snapshot_path
from namel3ss.ui.export.actions import build_actions_export
from namel3ss.ui.export.schema import build_schema_export
from namel3ss.ui.export.ui import build_ui_export
from namel3ss.version import get_version

MANIFEST_FILENAME = "manifest.json"
ENTRY_FILENAME = "entry.json"
UI_DIRNAME = "ui"
WEB_DIRNAME = "web"
PROD_HTML_FILENAME = "prod.html"
RUNTIME_WEB_ASSETS = ("runtime.css", "runtime.js")
STUDIO_WEB_ASSETS = (
    "studio_ui.css",
    "styles/layout_tokens.css",
    "styles/theme.css",
    "theme_tokens.css",
    "theme_tokens.js",
    "theme_runtime.js",
    "ui_renderer.js",
    "ui_renderer_chart.js",
    "ui_renderer_chat.js",
    "ui_renderer_upload.js",
    "ui_renderer_collections.js",
    "ui_renderer_form.js",
)
_TEXT_ASSET_SUFFIXES = {".css", ".html", ".js"}


def prepare_build_dir(project_root: Path, target: str, build_id: str) -> Path:
    path = build_dir(project_root, target, build_id)
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_program_bundle(build_path: Path, project_root: Path, sources: Dict[Path, str]) -> list[dict]:
    program_root = build_path / "program"
    program_root.mkdir(parents=True, exist_ok=True)
    fingerprints = []
    for src_path, text in sorted(sources.items(), key=lambda item: item[0].as_posix()):
        try:
            rel = src_path.resolve().relative_to(project_root.resolve())
        except ValueError:
            rel = Path(src_path.name)
        dest = program_root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text, encoding="utf-8")
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        fingerprints.append({"path": rel.as_posix(), "sha256": digest})
    return sorted(fingerprints, key=lambda item: item["path"])


def build_metadata(
    *,
    build_id: str,
    target: str,
    process_model: str,
    safe_config: Dict[str, object],
    program_summary: Dict[str, object],
    lock_digest: str,
    lock_snapshot: Dict[str, object],
    fingerprints: list[dict],
    recommended_persistence: str,
    app_relative_path: str,
    artifacts: dict,
    entry_instructions: dict,
) -> Dict[str, object]:
    return {
        "build_id": build_id,
        "target": target,
        "process_model": process_model,
        "target_info": {
            "name": target,
            "process_model": process_model,
            "recommended_persistence": recommended_persistence,
        },
        "app_relative_path": app_relative_path,
        "namel3ss_version": get_version(),
        "config_summary": safe_config,
        "persistence_target": safe_config.get("persistence", {}).get("target"),
        "recommended_persistence": recommended_persistence,
        "lockfile_digest": lock_digest,
        "lockfile_status": lock_snapshot.get("status"),
        "program_summary": program_summary,
        "source_fingerprints": fingerprints,
        "artifacts": artifacts,
        "entry_instructions": entry_instructions,
    }


def write_manifest(build_path: Path, manifest: dict) -> str:
    path = build_path / MANIFEST_FILENAME
    payload = manifest if isinstance(manifest, dict) else {}
    write_json(path, payload)
    return MANIFEST_FILENAME


def build_entry_instructions(target: str, build_id: str) -> dict:
    instructions = {
        "run": f"n3 run --target {target} --build {build_id}",
        "stop": "Stop the process with Ctrl+C.",
    }
    if target == "service":
        instructions["start"] = "n3 start --target service"
        instructions["health"] = "GET http://127.0.0.1:8787/health"
    if target == "edge":
        instructions["note"] = "Edge target runs as a simulator."
    return instructions


def write_entry_instructions(build_path: Path, instructions: dict) -> str:
    path = build_path / ENTRY_FILENAME
    write_json(path, instructions if isinstance(instructions, dict) else {})
    return ENTRY_FILENAME


def write_schema_snapshot(build_path: Path, snapshot: dict) -> str:
    path = build_snapshot_path(build_path)
    write_json(path, snapshot)
    return path.relative_to(build_path).as_posix()


def write_ui_contract(build_path: Path, program_ir, manifest: dict) -> dict:
    ui_dir = build_path / UI_DIRNAME
    ui_dir.mkdir(parents=True, exist_ok=True)
    ui_export = build_ui_export(manifest)
    actions_export = build_actions_export(manifest)
    schema_export = build_schema_export(program_ir, manifest)
    write_json(ui_dir / "ui.json", ui_export)
    write_json(ui_dir / "actions.json", actions_export)
    write_json(ui_dir / "schema.json", schema_export)
    return {
        "ui": f"{UI_DIRNAME}/ui.json",
        "actions": f"{UI_DIRNAME}/actions.json",
        "schema": f"{UI_DIRNAME}/schema.json",
    }


def write_web_bundle(build_path: Path) -> str:
    web_root = build_path / WEB_DIRNAME
    web_root.mkdir(parents=True, exist_ok=True)
    runtime_root = _runtime_web_root()
    prod_src = runtime_root / PROD_HTML_FILENAME
    _copy_asset(prod_src, web_root / "index.html")
    for name in RUNTIME_WEB_ASSETS:
        _copy_asset(runtime_root / name, web_root / name)
    studio_root = studio_web_root()
    for name in STUDIO_WEB_ASSETS:
        _copy_asset(studio_root / name, web_root / name)
    return WEB_DIRNAME


def write_service_bundle(build_path: Path, build_id: str) -> None:
    bundle_root = build_path / "service"
    bundle_root.mkdir(parents=True, exist_ok=True)
    instructions = "\n".join(
        [
            "namel3ss service bundle",
            f"Build: {build_id}",
            "",
            "Run the promoted build locally:",
            f"  n3 run --target service --build {build_id}",
            "",
            "Health endpoint (default port 8787):",
            "  GET http://127.0.0.1:8787/health",
        ]
    )
    (bundle_root / "README.txt").write_text(instructions.strip() + "\n", encoding="utf-8")


def write_edge_stub(build_path: Path, build_id: str) -> None:
    stub_root = build_path / "edge"
    stub_root.mkdir(parents=True, exist_ok=True)
    note = "\n".join(
        [
            "Edge simulator bundle",
            "This build records the inputs but does not generate a runnable edge package yet.",
            f"Run: n3 run --target edge --build {build_id}",
        ]
    )
    (stub_root / "README.txt").write_text(note.strip() + "\n", encoding="utf-8")


def _copy_asset(src: Path, dest: Path) -> None:
    if not src.exists():
        raise Namel3ssError(
            build_guidance_message(
                what=f"Missing runtime asset: {src.name}.",
                why="Build could not copy required runtime assets.",
                fix="Reinstall namel3ss or re-run the build after restoring assets.",
                example="n3 build --target service",
            )
        )
    dest.parent.mkdir(parents=True, exist_ok=True)
    if src.suffix.lower() in _TEXT_ASSET_SUFFIXES:
        _copy_text_asset(src, dest)
    else:
        dest.write_bytes(src.read_bytes())


def _copy_text_asset(src: Path, dest: Path) -> None:
    text = src.read_text(encoding="utf-8")
    normalized = _normalize_text_asset(text)
    dest.write_text(normalized, encoding="utf-8", newline="\n")


def _normalize_text_asset(text: str) -> str:
    lines = [line.rstrip() for line in text.splitlines()]
    if not lines:
        return ""
    return "\n".join(lines) + "\n"


def _runtime_web_root() -> Path:
    return package_root() / "runtime" / "web"


__all__ = [
    "BUILD_META_FILENAME",
    "ENTRY_FILENAME",
    "MANIFEST_FILENAME",
    "STUDIO_WEB_ASSETS",
    "UI_DIRNAME",
    "WEB_DIRNAME",
    "build_entry_instructions",
    "build_metadata",
    "prepare_build_dir",
    "write_edge_stub",
    "write_entry_instructions",
    "write_manifest",
    "write_program_bundle",
    "write_schema_snapshot",
    "write_service_bundle",
    "write_ui_contract",
    "write_web_bundle",
]
