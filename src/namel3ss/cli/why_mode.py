from __future__ import annotations

from dataclasses import dataclass

from namel3ss.cli.app_path import resolve_app_path
from namel3ss.cli.first_run import is_first_run
from namel3ss.cli.learning_support import (
    build_learning_context,
    collect_capsules,
    collect_requires,
    require_app_path,
    summarize_pages,
    summarize_records,
)
from namel3ss.config.loader import load_config
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.secrets import collect_secret_values, redact_payload
from namel3ss.utils.json_tools import dumps_pretty


@dataclass
class _WhyParams:
    app_arg: str | None
    json_mode: bool
    audience: str
    technical: bool


def run_why_command(args: list[str]) -> int:
    params = _parse_args(args)
    app_path = resolve_app_path(params.app_arg)
    require_app_path(app_path)
    if params.json_mode or params.technical or not is_first_run(app_path.parent, args):
        payload = build_why_payload(app_path)
        if params.json_mode:
            print(dumps_pretty(payload))
            return 0
        lines = build_why_lines(payload, audience=params.audience)
        _write_human_lines(lines)
        return 0
    ctx = build_learning_context(app_path)
    lines = _build_first_run_lines(ctx)
    _write_human_lines(lines)
    return 0


def build_why_payload(app_path) -> dict:
    ctx = build_learning_context(app_path)
    capsules = collect_capsules(ctx.project_root, ctx.modules)
    requires = collect_requires(ctx.program)
    payload = {
        "schema_version": 1,
        "engine_target": ctx.engine_target,
        "proof_id": ctx.proof_id,
        "verify_status": ctx.verify_status or "unknown",
        "persistence": ctx.persistence,
        "capsules": capsules,
        "requires": requires,
        "flows": len(ctx.program.flows),
        "pages": len(ctx.program.pages),
        "records": len(ctx.program.records),
    }
    config = load_config(app_path=app_path, root=ctx.project_root)
    redacted = redact_payload(payload, collect_secret_values(config))
    return redacted if isinstance(redacted, dict) else payload


def build_why_lines(payload: dict, *, audience: str) -> list[str]:
    if audience == "non_technical":
        return _build_non_technical_lines(payload)
    return _build_default_lines(payload)


def _build_default_lines(payload: dict) -> list[str]:
    lines = ["- Why this app is safe to run."]
    lines.append(f"- Engine target: {payload.get('engine_target', 'unknown')}")
    lines.append(
        f"- App shape: {payload.get('pages', 0)} pages, {payload.get('flows', 0)} flows, {payload.get('records', 0)} records"
    )
    lines.append(f"- Capsules: {_format_capsules(payload.get('capsules', []))}")
    lines.append(f"- Access rules: {_format_requires(payload.get('requires', []))}")
    lines.append(f"- Persistence: {_format_persistence(payload.get('persistence', {}))}")
    proof_id = payload.get("proof_id") or "none"
    lines.append(f"- Proof: {proof_id}")
    verify_status = payload.get("verify_status") or "unknown"
    lines.append(f"- Verify: {verify_status}")
    return lines[:15]


def _build_non_technical_lines(payload: dict) -> list[str]:
    pages = payload.get("pages", 0)
    flows = payload.get("flows", 0)
    lines = ["- What this app is doing."]
    lines.append(f"- {pages} screens and {flows} flows are defined.")
    lines.append(f"- Access is gated by {_format_requires(payload.get('requires', []), short=True)}")
    lines.append(f"- Data is stored in {_format_persistence(payload.get('persistence', {}))}.")
    proof_id = payload.get("proof_id") or "none"
    lines.append(f"- Latest proof: {proof_id}.")
    verify_status = payload.get("verify_status") or "unknown"
    lines.append(f"- Last verify: {verify_status}.")
    return lines[:15]


def _format_capsules(capsules: list[dict]) -> str:
    if not capsules:
        return "none"
    parts = [f"{item.get('name')} source {item.get('source')}" for item in capsules]
    return ", ".join(parts)


def _format_requires(rules: list[dict], short: bool = False) -> str:
    if not rules:
        return "no explicit rules"
    limit = 2 if short else 3
    parts = []
    for rule in rules[:limit]:
        scope = rule.get("scope")
        name = rule.get("name")
        expr = rule.get("rule")
        parts.append(f"{scope} {name} requires {expr}")
    if len(rules) > limit:
        parts.append("…")
    return "; ".join(parts)


def _format_persistence(persistence: dict) -> str:
    target = persistence.get("target") or "memory"
    descriptor = persistence.get("descriptor")
    if descriptor:
        return f"{target} {descriptor}"
    return str(target)


def _write_human_lines(lines: list[str]) -> None:
    print("\n".join(lines))


def _parse_args(args: list[str]) -> _WhyParams:
    app_arg = None
    json_mode = False
    audience = "default"
    technical = False
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--json":
            json_mode = True
            i += 1
            continue
        if arg == "--technical":
            technical = True
            i += 1
            continue
        if arg == "--first-run":
            i += 1
            continue
        if arg == "--non-technical":
            audience = "non_technical"
            i += 1
            continue
        if arg.startswith("--"):
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Unknown flag '{arg}'.",
                    why="Supported flags: --json, --non-technical, --technical.",
                    fix="Remove the unsupported flag.",
                    example="n3 why --json",
                )
            )
        if app_arg is None:
            app_arg = arg
            i += 1
            continue
        raise Namel3ssError(
            build_guidance_message(
                what="Too many positional arguments.",
                why="why accepts at most one app path.",
                fix="Provide a single app.ai path or none.",
                example="n3 why app.ai",
            )
        )
    return _WhyParams(app_arg=app_arg, json_mode=json_mode, audience=audience, technical=technical)


def _build_first_run_lines(ctx) -> list[str]:
    pages = summarize_pages(ctx.program)
    records = summarize_records(ctx.program)
    flows = sorted(flow.name for flow in ctx.program.flows)
    ai_names = sorted(ctx.program.ais.keys()) if getattr(ctx.program, "ais", None) else []
    tool_names = sorted(ctx.program.tools.keys()) if getattr(ctx.program, "tools", None) else []

    lines = ["What this app does"]
    screen_label = _pluralize(len(pages), "screen")
    action_label = _pluralize(len(flows), "action")
    lines.append(f"- Provides {len(pages)} {screen_label} with {len(flows)} {action_label}.")
    if pages:
        sample_pages = ", ".join(pages[:3])
        suffix = "…" if len(pages) > 3 else ""
        lines.append(f"- Screens include: {sample_pages}{suffix}.")

    lines.append("What data it works with")
    if records:
        sample_records = ", ".join(records[:5])
        suffix = "…" if len(records) > 5 else ""
        lines.append(f"- Records: {sample_records}{suffix}.")
    else:
        lines.append("- No records are defined.")

    lines.append("How AI is involved")
    if ai_names:
        sample_ai = ", ".join(ai_names[:3])
        suffix = "…" if len(ai_names) > 3 else ""
        lines.append(f"- Uses AI profiles: {sample_ai}{suffix}.")
    else:
        lines.append("- No AI calls are defined.")

    lines.append("External tools")
    if tool_names:
        sample_tools = ", ".join(tool_names[:3])
        suffix = "…" if len(tool_names) > 3 else ""
        lines.append(f"- Tool integrations: {sample_tools}{suffix}.")
    else:
        lines.append("- No external tools are configured.")
    return lines[:20]


def _pluralize(count: int, singular: str, plural: str | None = None) -> str:
    if count == 1:
        return singular
    return plural or f"{singular}s"


__all__ = ["build_why_payload", "build_why_lines", "run_why_command", "_write_human_lines"]
