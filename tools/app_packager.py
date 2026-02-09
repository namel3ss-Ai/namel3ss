from __future__ import annotations

from pathlib import Path

from namel3ss.cli.app_loader import load_program
from namel3ss.config.loader import load_config
from namel3ss.determinism import canonical_json_dumps
from namel3ss.errors.base import Namel3ssError
from namel3ss.ir.serialize import dump_ir
from namel3ss.runtime.capabilities.feature_gate import require_app_capability
from namel3ss.ui.manifest.app_descriptor import build_app_descriptor
from namel3ss.validation_entrypoint import build_static_manifest
from tools.app_archive import ARCHIVE_EXTENSION, build_archive_bytes, sha256_bytes, write_archive


REQUIRED_CAPABILITY = "app_packaging"


def build_app_archive(app_path: Path, *, out_path: Path | None = None) -> dict[str, object]:
    app_file = _validate_app_file(app_path)
    entries, descriptor = build_app_entries(app_file)
    target = Path(out_path) if out_path is not None else app_file.with_suffix(ARCHIVE_EXTENSION)
    checksum = write_archive(target, entries)
    return {
        "ok": True,
        "archive": str(target.resolve()),
        "checksum": checksum,
        "app": descriptor.get("app"),
    }


def build_app_entries(app_path: Path) -> tuple[dict[str, bytes], dict[str, object]]:
    app_file = _validate_app_file(app_path)
    require_app_capability(app_file, REQUIRED_CAPABILITY)

    program_ir, _sources = load_program(app_file.as_posix())
    config = load_config(app_path=app_file)
    manifest = build_static_manifest(program_ir, config=config, state={}, store=None, warnings=[])

    descriptor = build_app_descriptor(program_ir, manifest, app_path=app_file)
    payloads: dict[str, bytes] = {
        "compiled_ir.json": _encode_json(dump_ir(program_ir)),
        "ui_manifest.json": _encode_json(manifest),
        "permissions.json": _encode_json(descriptor.get("permissions", {})),
        "ui_state_schema.json": _encode_json(descriptor.get("ui_state", {})),
        "runtime_config.json": _encode_json(descriptor.get("runtime_config", {})),
        "static_assets.json": _encode_json({"assets": []}),
    }

    file_checksums = {
        name: sha256_bytes(payload)
        for name, payload in sorted(payloads.items(), key=lambda item: item[0])
    }
    descriptor["checksums"] = {
        "content": sha256_bytes(_encode_json(file_checksums)),
        "files": file_checksums,
    }
    payloads["app_descriptor.json"] = _encode_json(descriptor)
    return payloads, descriptor


def inspect_source_app(app_path: Path) -> dict[str, object]:
    entries, descriptor = build_app_entries(app_path)
    archive_checksum = sha256_bytes(build_archive_bytes(entries))
    return {
        "app": descriptor.get("app", {}).get("name"),
        "permissions": descriptor.get("permissions", {}),
        "pages": descriptor.get("pages", []),
        "ui_state": descriptor.get("ui_state", {}),
        "capabilities": descriptor.get("capabilities", []),
        "checksum": archive_checksum,
        "namel3ss_version": descriptor.get("namel3ss_version"),
    }


def _validate_app_file(app_path: Path) -> Path:
    path = Path(app_path)
    if path.suffix != ".ai":
        raise Namel3ssError("This file is not a namel3ss app.")
    if not path.exists() or not path.is_file():
        raise Namel3ssError("This file is not a namel3ss app.")
    return path.resolve()


def _encode_json(payload: object) -> bytes:
    return canonical_json_dumps(payload, pretty=True, drop_run_keys=False).encode("utf-8")


__all__ = ["build_app_archive", "build_app_entries", "inspect_source_app", "REQUIRED_CAPABILITY"]
