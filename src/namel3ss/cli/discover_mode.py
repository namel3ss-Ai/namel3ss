from __future__ import annotations

from namel3ss.cli.app_path import resolve_app_path
from namel3ss.config.loader import load_config
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.registry.ops import discover_registry
from namel3ss.utils.json_tools import dumps_pretty


def run_discover(args: list[str], *, json_mode: bool) -> int:
    if not args or args[0] in {"help", "-h", "--help"}:
        _print_usage()
        return 0
    phrase = None
    capability = None
    risk = None
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
    matches = discover_registry(app_root, config, phrase=phrase, capability=capability, risk=risk)
    payload = {
        "status": "ok",
        "phrase": phrase,
        "count": len(matches),
        "results": [_match_payload(match) for match in matches],
    }
    if json_mode:
        print(dumps_pretty(payload))
        return 0
    print(f"Discover results: {len(matches)}")
    for match in matches:
        entry = match.entry
        pack_id = entry.get("pack_id")
        pack_name = entry.get("pack_name")
        pack_version = entry.get("pack_version")
        trusted = "trusted" if match.trusted else "unverified"
        line = f"- {pack_name} {pack_id}@{pack_version} status {trusted} risk {match.risk}"
        if match.blocked:
            line += " blocked"
        print(line)
        tools = entry.get("tools") if isinstance(entry.get("tools"), list) else []
        if tools:
            print(f"  tools: {', '.join(str(tool) for tool in tools)}")
        if match.matched_tokens:
            print(f"  matched: {', '.join(match.matched_tokens)}")
        if match.blocked_reasons:
            print(f"  policy: {'; '.join(match.blocked_reasons)}")
    return 0


def _match_payload(match) -> dict[str, object]:
    entry = match.entry
    return {
        "pack_id": entry.get("pack_id"),
        "pack_name": entry.get("pack_name"),
        "pack_version": entry.get("pack_version"),
        "tools": entry.get("tools"),
        "capabilities": entry.get("capabilities"),
        "source": entry.get("source"),
        "trusted": match.trusted,
        "risk": match.risk,
        "blocked_by_policy": match.blocked,
        "blocked_reasons": match.blocked_reasons,
        "match_score": match.match_score,
        "matched_tokens": match.matched_tokens,
    }


def _next_value(args: list[str], idx: int, flag: str) -> str:
    if idx + 1 >= len(args):
        raise Namel3ssError(_missing_flag_message(flag))
    value = args[idx + 1]
    if not value or value.startswith("--"):
        raise Namel3ssError(_missing_flag_message(flag))
    return value


def _print_usage() -> None:
    usage = """Usage:
  n3 discover intent_phrase --capability network|filesystem|secrets|subprocess|env --risk low|medium|high --json
  Notes:
    flags are optional unless stated
"""
    print(usage.strip())


def _missing_phrase_message() -> str:
    return build_guidance_message(
        what="Intent phrase is missing.",
        why="You must provide a phrase to discover packs.",
        fix="Pass an intent phrase.",
        example='n3 discover "send email securely"',
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
        why="n3 discover only accepts --capability and --risk.",
        fix="Remove the extra arguments.",
        example='n3 discover "send email" --capability network',
    )


def _invalid_capability_message(value: str) -> str:
    return build_guidance_message(
        what=f"Unsupported capability filter '{value}'.",
        why="Capability filters must be network, filesystem, secrets, subprocess, or env.",
        fix="Use a supported capability filter.",
        example='n3 discover "email" --capability network',
    )


def _invalid_risk_message(value: str) -> str:
    return build_guidance_message(
        what=f"Unsupported risk filter '{value}'.",
        why="Risk filters must be low, medium, or high.",
        fix="Use a supported risk filter.",
        example='n3 discover "email" --risk medium',
    )


__all__ = ["run_discover"]
