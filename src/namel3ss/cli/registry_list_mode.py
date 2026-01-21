from __future__ import annotations

from pathlib import Path

from namel3ss.cli.app_path import resolve_app_path
from namel3ss.config.loader import load_config
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.packs.policy import load_pack_policy
from namel3ss.runtime.packs.registry import load_pack_registry
from namel3ss.runtime.registry.catalog import build_catalog
from namel3ss.runtime.registry.resolver import resolve_registry_entries
from namel3ss.utils.json_tools import dumps_pretty


def run_registry_list(args: list[str], *, json_mode: bool) -> int:
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
        raise Namel3ssError(_unknown_args_message([item]))
    app_path = resolve_app_path(None)
    app_root = app_path.parent
    config = load_config(root=app_root)
    resolution = resolve_registry_entries(
        app_root,
        config,
        registry_id=registry_id,
        registry_url=registry_url,
        phrase="",
        capability=None,
        risk=None,
        offline=offline,
    )
    policy = load_pack_policy(app_root)
    installed_versions = _installed_versions(app_root, config)
    packs = build_catalog(
        resolution.entries,
        policy=policy,
        installed_versions=installed_versions,
        app_root=app_root,
    )
    payload = {
        "status": "ok",
        "count": len(packs),
        "sources": _sources_payload(resolution),
        "selected_sources": list(resolution.selected_ids),
        "packs": [
            {
                "pack_id": pack.pack_id,
                "pack_name": pack.pack_name,
                "installed_version": pack.installed_version,
                "latest_version": pack.latest_version,
                "versions": list(pack.versions),
            }
            for pack in packs
        ],
    }
    if json_mode:
        print(dumps_pretty(payload))
        return 0
    print(f"Registry packs: {len(packs)}")
    for pack in packs:
        latest = pack.latest_version or "none"
        status = _latest_status(pack.versions)
        risk = _latest_risk(pack.versions)
        line = f"- {pack.pack_name} {pack.pack_id} latest {latest} trust {status} risk {risk}"
        if pack.installed_version:
            line += f" installed {pack.installed_version}"
        print(line)
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


def _latest_status(versions: list[dict[str, object]]) -> str:
    if not versions:
        return "unknown"
    trust = versions[0].get("trust")
    if isinstance(trust, dict):
        status = trust.get("status")
        if isinstance(status, str):
            return status
    return "unknown"


def _latest_risk(versions: list[dict[str, object]]) -> str:
    if not versions:
        return "unknown"
    risk = versions[0].get("risk")
    return risk if isinstance(risk, str) else "unknown"


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


def _unknown_args_message(args: list[str]) -> str:
    joined = " ".join(args)
    return build_guidance_message(
        what=f"Unknown arguments: {joined}.",
        why="n3 registry list only accepts registry selection flags.",
        fix="Remove the extra arguments.",
        example="n3 registry list --registry local",
    )


def _missing_flag_message(flag: str) -> str:
    return build_guidance_message(
        what=f"{flag} is missing a value.",
        why="Flags must be followed by a value.",
        fix=f"Provide a value after {flag}.",
        example=f"{flag} local",
    )


__all__ = ["run_registry_list"]
