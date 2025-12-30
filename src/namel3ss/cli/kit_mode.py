from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from namel3ss.cli.app_path import resolve_app_path
from namel3ss.cli.learning_support import (
    build_learning_context,
    collect_capsules,
    collect_requires,
    summarize_flows,
    summarize_graph,
    summarize_pages,
    summarize_records,
)
from namel3ss.config.loader import load_config
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.pkg.lockfile import LOCKFILE_FILENAME
from namel3ss.secrets import collect_secret_values, redact_text


@dataclass(frozen=True)
class _KitParams:
    app_arg: str | None
    output_format: str
    technical: bool


def run_kit_command(args: list[str]) -> int:
    params = _parse_args(args)
    if params.output_format != "md":
        raise Namel3ssError(
            build_guidance_message(
                what="Only markdown kits are supported right now.",
                why=f"Requested format '{params.output_format}' is not available.",
                fix="Use --format md.",
                example="n3 kit --format md",
            )
        )
    app_path = resolve_app_path(params.app_arg)
    kit_text = build_kit_markdown(app_path, technical=params.technical)
    config = load_config(app_path=app_path, root=app_path.parent)
    secret_values = collect_secret_values(config)
    safe_text = redact_text(kit_text, secret_values)
    kit_path = _write_kit(app_path.parent, safe_text, technical=params.technical)
    print(f"Kit written to {kit_path.as_posix()}")
    return 0


def build_kit_markdown(app_path: Path, *, technical: bool) -> str:
    ctx = build_learning_context(app_path)
    capsules = collect_capsules(ctx.project_root, ctx.modules)
    requires = collect_requires(ctx.program)
    pages = summarize_pages(ctx.program)
    flows = summarize_flows(ctx.program)
    records = summarize_records(ctx.program)
    graph_lines = summarize_graph(ctx.graph)
    package_summary = _summarize_packages(ctx.project_root)
    title = app_path.parent.name
    lines: list[str] = []
    lines.append(f"# Adoption kit: {title}")
    lines.append("")
    lines.append("## What the app does")
    lines.append(f"- Pages: {', '.join(pages) if pages else 'none'}")
    lines.append(f"- Flows: {', '.join(flows) if flows else 'none'}")
    lines.append(f"- Records: {', '.join(records) if records else 'none'}")
    lines.append("")
    lines.append("## Access rules")
    if requires:
        for rule in requires[:5]:
            lines.append(f"- {rule['scope']} {rule['name']} requires {rule['rule']}")
    else:
        lines.append("- No explicit requires rules found.")
    lines.append("")
    lines.append("## Data & identity")
    lines.append(f"- Persistence: {_format_persistence(ctx.persistence)}")
    lines.append(f"- Identity fields: {_format_identity(ctx.program)}")
    lines.append("")
    lines.append("## Trust posture")
    lines.append(f"- Proof id: {ctx.proof_id or 'none'}")
    lines.append(f"- Verify status: {ctx.verify_status or 'unknown'}")
    lines.append(f"- Package licenses: {package_summary}")
    if not ctx.proof_id or ctx.verify_status in {None, "unknown"}:
        lines.append("- Note: Run n3 verify --prod to include trust details.")
    lines.append("")
    lines.append("## Architecture")
    lines.append(f"- Capsules: {_format_capsules(capsules)}")
    lines.append("- Dependency graph:")
    if graph_lines:
        lines.extend([f"  - {line}" for line in graph_lines])
    else:
        lines.append("  - none")
    lines.append("")
    lines.append("## How to run")
    lines.append("- n3 test")
    lines.append("- n3 verify --prod")
    lines.append("- n3 studio")
    if technical:
        lines.append("")
        lines.append("## Technical notes")
        lines.append(f"- Engine target: {ctx.engine_target}")
        lines.append("- Proof and verify outputs are deterministic and redacted.")
    return "\n".join(lines) + "\n"


def _summarize_packages(project_root: Path) -> str:
    lock_path = project_root / LOCKFILE_FILENAME
    if not lock_path.exists():
        return "no lockfile"
    try:
        data = lock_path.read_text(encoding="utf-8")
    except OSError:
        return "lockfile unreadable"
    try:
        payload = json.loads(data)
    except Exception:
        return "lockfile invalid"
    packages = payload.get("packages", []) if isinstance(payload, dict) else []
    if not packages:
        return "none"
    parts = []
    for pkg in sorted(packages, key=lambda p: p.get("name", "")):
        name = pkg.get("name")
        license_id = pkg.get("license") or pkg.get("license_file") or "unknown"
        parts.append(f"{name} license {license_id}")
    return ", ".join(parts)


def _format_capsules(capsules: list[dict]) -> str:
    if not capsules:
        return "none"
    return ", ".join(f"{c['name']} source {c['source']}" for c in capsules)


def _format_persistence(persistence: dict) -> str:
    target = persistence.get("target") or "memory"
    descriptor = persistence.get("descriptor")
    return f"{target} {descriptor}" if descriptor else str(target)


def _format_identity(program) -> str:
    identity = getattr(program, "identity", None)
    if not identity:
        return "none"
    fields = [field.name for field in identity.fields]
    return ", ".join(sorted(fields)) if fields else "none"


def _write_kit(project_root: Path, content: str, *, technical: bool) -> Path:
    kit_dir = project_root / ".namel3ss" / "kit"
    kit_dir.mkdir(parents=True, exist_ok=True)
    filename = "adoption-technical.md" if technical else "adoption.md"
    path = kit_dir / filename
    path.write_text(content, encoding="utf-8")
    return path


def _parse_args(args: list[str]) -> _KitParams:
    app_arg = None
    output_format = "md"
    technical = False
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--format":
            if i + 1 >= len(args):
                raise Namel3ssError(
                    build_guidance_message(
                        what="--format flag is missing a value.",
                        why="Kit needs a format value.",
                        fix="Use md.",
                        example="n3 kit --format md",
                    )
                )
            output_format = args[i + 1]
            i += 2
            continue
        if arg == "--technical":
            technical = True
            i += 1
            continue
        if arg == "--non-technical":
            technical = False
            i += 1
            continue
        if arg.startswith("--"):
            raise Namel3ssError(
                build_guidance_message(
                    what=f"Unknown flag '{arg}'.",
                    why="Supported flags: --format, --technical, --non-technical.",
                    fix="Remove the unsupported flag.",
                    example="n3 kit --format md",
                )
            )
        if app_arg is None:
            app_arg = arg
            i += 1
            continue
        raise Namel3ssError(
            build_guidance_message(
                what="Too many positional arguments.",
                why="kit accepts at most one app path.",
                fix="Provide a single app.ai path or none.",
                example="n3 kit app.ai",
            )
        )
    return _KitParams(app_arg=app_arg, output_format=output_format, technical=technical)


__all__ = ["build_kit_markdown", "run_kit_command"]
