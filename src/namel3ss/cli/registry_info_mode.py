from __future__ import annotations

from pathlib import Path

from namel3ss.cli.app_path import resolve_app_path
from namel3ss.config.loader import load_config
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.packs.policy import load_pack_policy
from namel3ss.runtime.packs.registry import load_pack_registry
from namel3ss.runtime.registry.catalog import build_pack_info
from namel3ss.runtime.registry.resolver import resolve_registry_entries
from namel3ss.utils.json_tools import dumps_pretty


def run_registry_info(args: list[str], *, json_mode: bool) -> int:
    pack_id = None
    registry_id = None
    registry_url = None
    offline = False
    idx = 0
    while idx < len(args):
        item = args[idx]
        if item in {"--from", "--registry"}:
            value = _next_value(args, idx, item)
            registry_id, registry_url = _assign_registry(value, registry_id, registry_url)
            idx += 2
            continue
        if item.startswith("--from=") or item.startswith("--registry="):
            value = item.split("=", 1)[1]
            registry_id, registry_url = _assign_registry(value, registry_id, registry_url)
            idx += 1
            continue
        if item == "--offline":
            offline = True
            idx += 1
            continue
        if item.startswith("--"):
            raise Namel3ssError(_unknown_args_message([item]))
        if pack_id is None:
            pack_id = item
            idx += 1
            continue
        raise Namel3ssError(_unknown_args_message([item]))
    if not pack_id:
        raise Namel3ssError(_missing_pack_message())
    app_path = resolve_app_path(None)
    app_root = app_path.parent
    config = load_config(root=app_root)
    resolution = resolve_registry_entries(
        app_root,
        config,
        registry_id=registry_id,
        registry_url=registry_url,
        phrase=pack_id,
        capability=None,
        risk=None,
        offline=offline,
    )
    policy = load_pack_policy(app_root)
    installed_versions = _installed_versions(app_root, config)
    info = build_pack_info(
        resolution.entries,
        pack_id=pack_id,
        policy=policy,
        installed_versions=installed_versions,
        app_root=app_root,
    )
    if info is None:
        raise Namel3ssError(_pack_not_found_message(pack_id))
    payload = {
        "status": "ok",
        "pack_id": info.pack_id,
        "pack_name": info.pack_name,
        "installed_version": info.installed_version,
        "latest_version": info.latest_version,
        "versions": list(info.versions),
        "sources": _sources_payload(resolution),
        "selected_sources": list(resolution.selected_ids),
    }
    if json_mode:
        print(dumps_pretty(payload))
        return 0
    print(f"Registry pack: {info.pack_name} {info.pack_id}")
    if info.installed_version:
        print(f"Installed version: {info.installed_version}")
    if info.latest_version:
        print(f"Latest version: {info.latest_version}")
    print(f"Versions: {len(info.versions)}")
    for entry in info.versions:
        version = entry.get("pack_version")
        trust = _trust_status(entry)
        risk = entry.get("risk") if isinstance(entry.get("risk"), str) else "unknown"
        compatibility = _version_status(entry)
        line = f"- {version} trust {trust} risk {risk}"
        if compatibility:
            line += f" compatibility {compatibility}"
        print(line)
        caps = _capability_summary(entry.get("capabilities"))
        if caps:
            print(f"  capabilities: {caps}")
        policy_reasons = _policy_reasons(entry)
        if policy_reasons:
            print(f"  policy: {policy_reasons}")
    return 0


def _installed_versions(app_root: Path, config) -> dict[str, str]:
    registry = load_pack_registry(app_root, config)
    versions: dict[str, str] = {}
    for pack_id, pack in registry.packs.items():
        if pack.version:
            versions[pack_id] = pack.version
    return versions


def _sources_payload(resolution) -> list[dict[str, object]]:
    sources = []
    for source in resolution.sources:
        sources.append(
            {
                "id": source.id,
                "kind": source.kind,
                "url": source.url if source.kind == "http" else None,
            }
        )
    return sources


def _trust_status(entry: dict[str, object]) -> str:
    trust = entry.get("trust")
    if isinstance(trust, dict):
        status = trust.get("status")
        if isinstance(status, str):
            return status
    return "unknown"


def _policy_reasons(entry: dict[str, object]) -> str:
    trust = entry.get("trust")
    if not isinstance(trust, dict):
        return ""
    reasons = trust.get("policy_reasons")
    if isinstance(reasons, list) and reasons:
        return "; ".join(str(item) for item in reasons)
    return ""


def _version_status(entry: dict[str, object]) -> str:
    version = entry.get("version")
    if not isinstance(version, dict):
        return ""
    status = version.get("status")
    if isinstance(status, str) and status != "not_installed":
        return status
    return ""


def _capability_summary(value: object) -> str:
    if not isinstance(value, dict):
        return ""
    filesystem = value.get("filesystem") or "none"
    network = value.get("network") or "none"
    env = value.get("env") or "none"
    subprocess = value.get("subprocess") or "none"
    secrets = value.get("secrets")
    secrets_count = len(secrets) if isinstance(secrets, list) else 0
    return f"filesystem {filesystem}, network {network}, env {env}, subprocess {subprocess}, secrets {secrets_count}"


def _assign_registry(
    value: str,
    registry_id: str | None,
    registry_url: str | None,
) -> tuple[str | None, str | None]:
    if value.startswith("http://") or value.startswith("https://"):
        return registry_id, value
    return value, registry_url


def _next_value(args: list[str], idx: int, flag: str) -> str:
    if idx + 1 >= len(args):
        raise Namel3ssError(_missing_flag_message(flag))
    value = args[idx + 1]
    if not value or value.startswith("--"):
        raise Namel3ssError(_missing_flag_message(flag))
    return value


def _missing_pack_message() -> str:
    return build_guidance_message(
        what="Pack name is missing.",
        why="You must provide a pack id.",
        fix="Pass a pack id to inspect.",
        example="n3 registry info team.pack",
    )


def _pack_not_found_message(pack_id: str) -> str:
    return build_guidance_message(
        what=f'Pack "{pack_id}" was not found.',
        why="No matching registry entry is available.",
        fix="Check the registry source or search for a different pack.",
        example=f"n3 registry search {pack_id}",
    )


def _missing_flag_message(flag: str) -> str:
    return build_guidance_message(
        what=f"{flag} is missing a value.",
        why="Flags must be followed by a value.",
        fix=f"Provide a value after {flag}.",
        example=f"{flag} local",
    )


def _unknown_args_message(args: list[str]) -> str:
    return build_guidance_message(
        what=f"Unknown arguments: {' '.join(args)}.",
        why="n3 registry info accepts a pack id and registry selection flags.",
        fix="Remove the extra arguments.",
        example="n3 registry info team.pack --registry local",
    )


__all__ = ["run_registry_info"]
