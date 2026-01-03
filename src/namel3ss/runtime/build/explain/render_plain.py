from __future__ import annotations

from .normalize import stable_bullets, stable_truncate


def render_exists(manifest: dict, diff: dict | None = None) -> str:
    build_id = manifest.get("build_id") or ""
    created_at = manifest.get("created_at") or ""
    inputs = manifest.get("inputs") or {}
    source_fp = inputs.get("source_fingerprint") or ""
    guarantees = manifest.get("guarantees") or []
    constraints = manifest.get("constraints") or []

    lines: list[str] = []
    lines.append("Why this app exists in this form")
    lines.append("")
    lines.append("Build")
    lines.extend(stable_bullets([f"id: {build_id}", f"source: {source_fp[:12]}", f"created: {created_at}"]))
    lines.append("")
    lines.append("What this build guarantees")
    if guarantees:
        lines.extend(stable_bullets([stable_truncate(str(item)) for item in guarantees]))
    else:
        lines.extend(stable_bullets(["No guarantees were recorded."]))

    lines.append("")
    lines.append("What this build constrains")
    if constraints:
        lines.extend(stable_bullets([stable_truncate(str(item)) for item in constraints]))
    else:
        lines.extend(stable_bullets(["No constraints were recorded."]))

    lines.append("")
    lines.append("What changed since last build")
    if diff is None:
        lines.extend(stable_bullets(["No previous build recorded."]))
    else:
        lines.extend(stable_bullets(_diff_lines(diff)))

    lines.append("")
    lines.append("Where it is stored")
    lines.extend(stable_bullets([f".namel3ss/build/history/{build_id}.json"]))

    return "\n".join(lines).rstrip()


def _diff_lines(diff: dict) -> list[str]:
    lines: list[str] = []
    summary = diff.get("summary") or []
    if summary:
        lines.extend([str(item) for item in summary])
    files = diff.get("files_changed") or []
    for path in files:
        lines.append(f"changed: {path}")
    if not lines:
        lines.append("No changes recorded.")
    return lines


__all__ = ["render_exists"]
