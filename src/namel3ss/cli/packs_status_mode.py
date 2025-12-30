from __future__ import annotations

from namel3ss.cli.app_path import resolve_app_path
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.packs.capabilities import capabilities_summary, load_pack_capabilities
from namel3ss.runtime.packs.registry import load_pack_registry, pack_payload
from namel3ss.runtime.packs.source_meta import read_pack_source
from namel3ss.runtime.packs.config import read_pack_config
from namel3ss.utils.json_tools import dumps_pretty


def run_packs_status(args: list[str], *, json_mode: bool) -> int:
    if args:
        raise Namel3ssError(_unknown_args_message(args))
    app_path = resolve_app_path(None)
    app_root = app_path.parent
    config = read_pack_config(app_root)
    registry = load_pack_registry(app_root, _config_from_app(config))
    packs = [pack for pack in registry.packs.values()]
    payload = {
        "app_root": str(app_root),
        "packs": [_pack_status_payload(pack) for pack in packs],
        "enabled_packs": config.enabled_packs,
        "disabled_packs": config.disabled_packs,
        "pinned_tools": config.pinned_tools,
        "collisions": sorted(registry.collisions.keys()),
    }
    if json_mode:
        print(dumps_pretty(payload))
        return 0
    print(f"App root: {payload['app_root']}")
    print(f"Packs installed: {len(packs)}")
    for pack in sorted(packs, key=lambda item: item.pack_id):
        status = "enabled" if pack.enabled else "disabled"
        verify = "verified" if pack.verified else "unverified"
        source_info = _pack_source_info(pack)
        caps = _pack_capabilities_summary(pack)
        summary = _caps_summary_text(caps)
        line = f"- {pack.pack_id} status {status} verify {verify}"
        if source_info:
            line += f" source {source_info.get('source_type')}"
        if summary:
            line += f" caps {summary}"
        print(line)
    if payload["collisions"]:
        print("Pack tool collisions:")
        for tool_name in payload["collisions"]:
            print(f"- {tool_name}")
    return 0


def _config_from_app(config):
    from namel3ss.config.model import AppConfig, ToolPacksConfig

    app = AppConfig()
    app.tool_packs = ToolPacksConfig(
        enabled_packs=config.enabled_packs,
        disabled_packs=config.disabled_packs,
        pinned_tools=config.pinned_tools,
    )
    return app


def _pack_source_info(pack) -> dict[str, object]:
    if not pack.pack_root:
        return {"source_type": "builtin", "path": None}
    info = read_pack_source(pack.pack_root)
    if info is None:
        return {"source_type": "installed", "path": str(pack.pack_root)}
    return {"source_type": info.source_type, "path": info.path}


def _pack_capabilities_summary(pack) -> dict[str, object]:
    if not pack.pack_root:
        return {}
    try:
        capabilities = load_pack_capabilities(pack.pack_root)
    except Namel3ssError:
        return {}
    if not capabilities:
        return {}
    return capabilities_summary(capabilities)


def _pack_status_payload(pack) -> dict[str, object]:
    payload = pack_payload(pack)
    payload["source_info"] = _pack_source_info(pack)
    payload["capabilities_summary"] = _pack_capabilities_summary(pack)
    return payload


def _caps_summary_text(summary: dict[str, object]) -> str:
    levels = summary.get("levels") if summary else None
    if not isinstance(levels, dict):
        return ""
    secrets = summary.get("secrets") if summary else []
    secret_count = len(secrets) if isinstance(secrets, list) else 0
    return (
        f'fs={levels.get("filesystem", "none")},'
        f'net={levels.get("network", "none")},'
        f'env={levels.get("env", "none")},'
        f'sub={levels.get("subprocess", "none")},'
        f'secrets={secret_count}'
    )


def _unknown_args_message(args: list[str]) -> str:
    return build_guidance_message(
        what=f"Unknown arguments: {' '.join(args)}.",
        why="n3 packs status does not accept positional arguments.",
        fix="Remove the extra arguments.",
        example="n3 packs status",
    )


__all__ = ["run_packs_status"]
