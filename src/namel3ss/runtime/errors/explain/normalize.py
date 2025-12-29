from __future__ import annotations

import json
from pathlib import Path


def stable_join(items: list[str], sep: str = ", ") -> str:
    return sep.join(items)


def stable_bullets(lines: list[str]) -> list[str]:
    return [line if line.startswith("- ") else f"- {line}" for line in lines]


def stable_truncate(text: str, limit: int = 120) -> str:
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def build_plain_text(pack: dict) -> str:
    lines: list[str] = []
    lines.append(f"summary: {pack.get('summary') or ''}")
    lines.append(f"api_version: {pack.get('api_version') or ''}")
    lines.append(f"ok: {pack.get('ok')}")
    error = pack.get("error") or {}
    if error:
        lines.append(f"error.kind: {error.get('kind')}")
        lines.append(f"error.what: {error.get('what')}")
        if error.get("why"):
            lines.append(f"error.why: {error.get('why')}")
        where = error.get("where") or {}
        if where.get("flow_name"):
            lines.append(f"error.where.flow: {where.get('flow_name')}")
        if where.get("step_id"):
            lines.append(f"error.where.step: {where.get('step_id')}")
        if where.get("tool_name"):
            lines.append(f"error.where.tool: {where.get('tool_name')}")
        details = error.get("details") or {}
        if details.get("error_type"):
            lines.append(f"error.type: {details.get('error_type')}")
        if details.get("error_message"):
            lines.append(f"error.message: {details.get('error_message')}")
        lines.append(f"error.recoverable: {error.get('recoverable')}")
        impact = error.get("impact") or []
        lines.append(f"impact.count: {len(impact)}")
        for idx, entry in enumerate(impact, start=1):
            lines.append(f"impact.{idx}: {entry}")
        options = error.get("recovery_options") or []
        lines.append(f"recovery.count: {len(options)}")
        for idx, option in enumerate(options, start=1):
            lines.append(f"recovery.{idx}.id: {option.get('id')}")
            lines.append(f"recovery.{idx}.title: {option.get('title')}")
    return "\n".join(lines)


def write_last_error(root: Path, pack: dict, plain_text: str, text: str) -> None:
    errors_dir = root / ".namel3ss" / "errors"
    errors_dir.mkdir(parents=True, exist_ok=True)
    (errors_dir / "last.json").write_text(_stable_json(pack), encoding="utf-8")
    (errors_dir / "last.plain").write_text(plain_text.rstrip() + "\n", encoding="utf-8")
    (errors_dir / "last.fix.txt").write_text(text.rstrip() + "\n", encoding="utf-8")


def _stable_json(payload: object) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


__all__ = ["build_plain_text", "stable_bullets", "stable_join", "stable_truncate", "write_last_error"]
