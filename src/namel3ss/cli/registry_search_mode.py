from __future__ import annotations

from pathlib import Path

from namel3ss.cli.app_path import resolve_app_path
from namel3ss.config.loader import load_config
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.packs.policy import load_pack_policy
from namel3ss.runtime.packs.registry import load_pack_registry
from namel3ss.runtime.registry.catalog import build_search_results
from namel3ss.runtime.registry.resolver import resolve_registry_entries
from namel3ss.utils.json_tools import dumps_pretty


def run_registry_search(args: list[str], *, json_mode: bool) -> int:
    phrase = None
    capability = None
    risk = None
    registry_id = None
    registry_url = None
    offline = False
    idx = 0
    while idx < len(args):
        item = args[idx]
        if item == "--capability":
            capability = _next_value(args, idx, "--capability")
            idx += 2
            continue
        if item == "--risk":
            risk = _next_value(args, idx, "--risk")
            idx += 2
            continue
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
        if phrase is None:
            phrase = item
            idx += 1
            continue
        raise Namel3ssError(_unknown_args_message([item]))
    if not phrase:
        raise Namel3ssError(_missing_phrase_message())
    if capability and capability not in {"network", "filesystem", "secrets", "subprocess", "env"}:
        raise Namel3ssError(_invalid_capability_message(capability))
    if risk and risk not in {"low", "medium", "high"}:
        raise Namel3ssError(_invalid_risk_message(risk))
    app_path = resolve_app_path(None)
    app_root = app_path.parent
    config = load_config(root=app_root)
    resolution = resolve_registry_entries(
        app_root,
        config,
        registry_id=registry_id,
        registry_url=registry_url,
        phrase=phrase,
        capability=capability,
        risk=risk,
        offline=offline,
    )
    policy = load_pack_policy(app_root)
    installed_versions = _installed_versions(app_root, config)
    results = build_search_results(
        resolution.entries,
        phrase=phrase,
        policy=policy,
        installed_versions=installed_versions,
        app_root=app_root,
        capability=capability,
        risk=risk,
    )
    payload = {
        "status": "ok",
        "phrase": phrase,
        "count": len(results),
        "sources": _sources_payload(resolution),
        "selected_sources": list(resolution.selected_ids),
        "results": results,
    }
    if json_mode:
        print(dumps_pretty(payload))
        return 0
    print(f"Registry search results: {len(results)}")
    for entry in results:
        pack_id = entry.get("pack_id")
        pack_name = entry.get("pack_name")
        pack_version = entry.get("pack_version")
        trust = _trust_status(entry)
        risk_level = entry.get("risk") if isinstance(entry.get("risk"), str) else "unknown"
        line = f"- {pack_name} {pack_id}@{pack_version} trust {trust} risk {risk_level}"
        print(line)
        caps = _capability_summary(entry.get("capabilities"))
        if caps:
            print(f"  capabilities: {caps}")
        matched = entry.get("matched_tokens")
        if isinstance(matched, list) and matched:
            print(f"  matched: {', '.join(str(item) for item in matched)}")
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


def _missing_phrase_message() -> str:
    return build_guidance_message(
        what="Search phrase is missing.",
        why="You must provide a phrase to search the registry.",
        fix="Pass an intent phrase.",
        example='n3 registry search "send email"',
    )


def _missing_flag_message(flag: str) -> str:
    return build_guidance_message(
        what=f"{flag} is missing a value.",
        why="Flags must be followed by a value.",
        fix=f"Provide a value after {flag}.",
        example=f'{flag} network',
    )


def _unknown_args_message(args: list[str]) -> str:
    return build_guidance_message(
        what=f"Unknown arguments: {' '.join(args)}.",
        why="n3 registry search accepts a phrase and optional filters.",
        fix="Remove the extra arguments.",
        example='n3 registry search "send email" --capability network',
    )


def _invalid_capability_message(value: str) -> str:
    return build_guidance_message(
        what=f"Unsupported capability filter '{value}'.",
        why="Capability filters must be network, filesystem, secrets, subprocess, or env.",
        fix="Use a supported capability filter.",
        example='n3 registry search "email" --capability network',
    )


def _invalid_risk_message(value: str) -> str:
    return build_guidance_message(
        what=f"Unsupported risk filter '{value}'.",
        why="Risk filters must be low, medium, or high.",
        fix="Use a supported risk filter.",
        example='n3 registry search "email" --risk medium',
    )


__all__ = ["run_registry_search"]
