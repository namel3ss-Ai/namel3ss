from __future__ import annotations

import json
from pathlib import Path

from .diff import DiffResult
from .invariants import InvariantReport


def build_report(
    *,
    scenario_id: str,
    scenario_name: str,
    invariants: InvariantReport,
    diff: DiffResult,
) -> tuple[str, dict]:
    ok = invariants.ok and diff.ok
    payload = {
        "ok": ok,
        "scenario_id": scenario_id,
        "scenario_name": scenario_name,
        "invariants": invariants.as_dict(),
        "diff": diff.as_dict(),
    }
    lines: list[str] = []
    lines.append(f"Memory proof: {'ok' if ok else 'fail'}")
    lines.append(f"Scenario: {scenario_id} - {scenario_name}")
    if invariants.failures:
        lines.append("Invariant failures:")
        for failure in invariants.failures:
            lines.append(f"- {failure.get('message')}")
    if invariants.notes:
        lines.append("Invariant notes:")
        for note in invariants.notes:
            lines.append(f"- {note}")
    if diff.entries:
        lines.append("Diffs:")
        for entry in diff.entries:
            lines.append(f"What happened: {entry.what}")
            lines.append(f"Where: {entry.where}")
            lines.append(f"Why it matters: {entry.why}")
            lines.append(f"How to fix: {entry.fix}")
    return "\n".join(lines), payload


def build_plain_text(meta: dict) -> str:
    lines: list[str] = []
    scenario = meta.get("scenario", {})
    lines.append(f"scenario.id: {scenario.get('id')}")
    lines.append(f"scenario.name: {scenario.get('name')}")
    steps = meta.get("step_counts", {})
    lines.append(f"steps.total: {steps.get('total')}")
    lines.append(f"steps.recall: {steps.get('recall')}")
    lines.append(f"steps.record: {steps.get('record')}")
    lines.append(f"steps.admin: {steps.get('admin')}")
    counts = meta.get("memory_counts", {})
    lines.append(f"memory.short_term: {counts.get('short_term')}")
    lines.append(f"memory.semantic: {counts.get('semantic')}")
    lines.append(f"memory.profile: {counts.get('profile')}")
    cache_steps = meta.get("cache_versions_by_step") or []
    if cache_steps:
        last = cache_steps[-1]
        for entry in sorted(last.get("versions") or [], key=lambda item: (item.get("store_key"), item.get("kind"))):
            store_key = entry.get("store_key")
            kind = entry.get("kind")
            version = entry.get("version")
            lines.append(f"cache.{store_key}.{kind}: {version}")
    phase_steps = meta.get("phase_snapshots_by_step") or []
    if phase_steps:
        last = phase_steps[-1]
        for entry in sorted(last.get("phases") or [], key=lambda item: item.get("store_key")):
            store_key = entry.get("store_key")
            phase_id = entry.get("current_phase_id")
            lines.append(f"phase.{store_key}.current: {phase_id}")
    return "\n".join(lines)


def write_scenario_artifacts(
    *,
    root: Path,
    scenario_id: str,
    recall_steps: list[dict],
    write_steps: list[dict],
    meta: dict,
    plain_text: str,
    report_text: str,
    report_json: dict,
) -> None:
    root.mkdir(parents=True, exist_ok=True)
    scenario_dir = root / scenario_id
    scenario_dir.mkdir(parents=True, exist_ok=True)
    _write_json(scenario_dir / "recall_steps.json", recall_steps)
    _write_json(scenario_dir / "write_steps.json", write_steps)
    _write_json(scenario_dir / "meta.json", meta)
    _write_text(scenario_dir / "plain.txt", plain_text)
    _write_text(scenario_dir / "report.txt", report_text)
    _write_json(scenario_dir / "report.json", report_json)


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_text(path: Path, payload: str) -> None:
    path.write_text(payload.rstrip() + "\n", encoding="utf-8")


__all__ = ["build_plain_text", "build_report", "write_scenario_artifacts"]
