from __future__ import annotations

import shutil
import tempfile
import zipfile
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.packs.layout import pack_manifest_path, pack_path, packs_root
from namel3ss.runtime.packs.manifest import parse_pack_manifest
from namel3ss.runtime.packs.source_meta import PackSourceInfo, write_pack_source
from namel3ss.runtime.packs.verification import verify_pack as verify_pack_signature
from namel3ss.runtime.packs.config import read_pack_config, write_pack_config
from namel3ss.runtime.tools.bindings_yaml import parse_bindings_yaml
from namel3ss.utils.fs import remove_tree


def install_pack(app_root: Path, source_path: Path) -> str:
    source = _unpack_source(source_path)
    manifest = parse_pack_manifest(pack_manifest_path(source))
    _validate_pack_files(source, manifest.pack_id)
    target = pack_path(app_root, manifest.pack_id)
    if target.exists():
        raise Namel3ssError(_pack_exists_message(manifest.pack_id))
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, target)
    source_type = "bundle" if source_path.suffix == ".zip" else "directory"
    write_pack_source(target, PackSourceInfo(source_type=source_type, path=str(source_path.resolve())))
    return manifest.pack_id


def remove_pack(app_root: Path, pack_id: str) -> Path:
    target = pack_path(app_root, pack_id)
    if not target.exists():
        raise Namel3ssError(_pack_missing_message(pack_id))
    remove_tree(target)
    return target


def verify_pack(app_root: Path, pack_id: str) -> None:
    pack_dir = pack_path(app_root, pack_id)
    if not pack_dir.exists():
        raise Namel3ssError(_pack_missing_message(pack_id))
    manifest_path = pack_manifest_path(pack_dir)
    manifest = parse_pack_manifest(manifest_path)
    manifest_text = manifest_path.read_text(encoding="utf-8")
    tools_text = None
    tools_path = pack_dir / "tools.yaml"
    if tools_path.exists():
        tools_text = tools_path.read_text(encoding="utf-8")
    verify_pack_signature(
        app_root=app_root,
        pack_id=manifest.pack_id,
        version=manifest.version,
        manifest_text=manifest_text,
        tools_text=tools_text,
        pack_dir=pack_dir,
    )


def enable_pack(app_root: Path, pack_id: str) -> Path:
    config = read_pack_config(app_root)
    enabled = set(config.enabled_packs)
    disabled = set(config.disabled_packs)
    enabled.add(pack_id)
    disabled.discard(pack_id)
    updated = type(config)(
        enabled_packs=sorted(enabled),
        disabled_packs=sorted(disabled),
        pinned_tools=dict(config.pinned_tools),
    )
    return write_pack_config(app_root, updated)


def disable_pack(app_root: Path, pack_id: str) -> Path:
    config = read_pack_config(app_root)
    enabled = set(config.enabled_packs)
    disabled = set(config.disabled_packs)
    enabled.discard(pack_id)
    disabled.add(pack_id)
    updated = type(config)(
        enabled_packs=sorted(enabled),
        disabled_packs=sorted(disabled),
        pinned_tools=dict(config.pinned_tools),
    )
    return write_pack_config(app_root, updated)


def _unpack_source(source_path: Path) -> Path:
    if source_path.is_dir():
        return source_path
    if source_path.suffix == ".zip":
        temp_dir = Path(tempfile.mkdtemp(prefix="namel3ss_pack_"))
        with zipfile.ZipFile(source_path, "r") as archive:
            archive.extractall(temp_dir)
        manifest = pack_manifest_path(temp_dir)
        if manifest.exists():
            return temp_dir
        candidates = [path for path in temp_dir.rglob("pack.yaml")]
        if len(candidates) == 1:
            return candidates[0].parent
        raise Namel3ssError(_pack_missing_manifest_message(source_path))
    raise Namel3ssError(_pack_unknown_source_message(source_path))


def _validate_pack_files(pack_dir: Path, pack_id: str) -> None:
    manifest_path = pack_manifest_path(pack_dir)
    if not manifest_path.exists():
        raise Namel3ssError(_pack_missing_manifest_message(pack_dir))
    tools_path = pack_dir / "tools.yaml"
    if tools_path.exists():
        text = tools_path.read_text(encoding="utf-8")
        parse_bindings_yaml(text, tools_path)


def _pack_exists_message(pack_id: str) -> str:
    return build_guidance_message(
        what=f'Pack "{pack_id}" is already installed.',
        why="A pack with this id exists in .namel3ss/packs.",
        fix="Remove it first or choose a different pack id.",
        example=f"n3 packs remove {pack_id} --yes",
    )


def _pack_missing_message(pack_id: str) -> str:
    return build_guidance_message(
        what=f'Pack "{pack_id}" was not found.',
        why="No matching pack exists in .namel3ss/packs.",
        fix="Install the pack first.",
        example=f"n3 packs add ./packs/{pack_id}",
    )


def _pack_missing_manifest_message(source: Path) -> str:
    return build_guidance_message(
        what="Pack manifest is missing.",
        why=f"Expected pack.yaml in {source}.",
        fix="Provide a pack with a pack.yaml file.",
        example="pack.yaml",
    )


def _pack_unknown_source_message(source: Path) -> str:
    return build_guidance_message(
        what="Unsupported pack source.",
        why=f"Pack source must be a directory or .zip (got {source}).",
        fix="Point to a pack folder or zip file.",
        example="n3 packs add ./bundle.n3pack.zip",
    )


__all__ = ["disable_pack", "enable_pack", "install_pack", "remove_pack", "verify_pack"]
