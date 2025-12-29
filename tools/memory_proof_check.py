from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from namel3ss.runtime.memory.proof import (
    build_plain_text,
    build_report,
    check_invariants,
    diff_scenario,
    list_scenario_paths,
    load_scenario,
    normalize_meta,
    normalize_recall_steps,
    normalize_write_steps,
    write_scenario_artifacts,
)
from namel3ss.runtime.memory.proof.runner import run_scenario


def main() -> int:
    scenarios_dir = ROOT / "tests" / "memory_proof" / "scenarios"
    output_dir = ROOT / "tests" / "memory_proof" / "output"
    golden_dir = ROOT / "tests" / "memory_proof" / "golden"
    scenario_paths = list_scenario_paths(scenarios_dir)
    if not scenario_paths:
        print("No memory proof scenarios found.")
        return 1
    failures = 0
    for path in scenario_paths:
        scenario = load_scenario(path)
        run = run_scenario(scenario)
        invariants = check_invariants(run)
        run.meta["invariants"] = invariants.as_dict()
        normalized = {
            "recall_steps": normalize_recall_steps(run.recall_steps),
            "write_steps": normalize_write_steps(run.write_steps),
            "meta": normalize_meta(run.meta),
        }
        golden_bundle = _load_bundle(golden_dir, scenario.scenario_id)
        if golden_bundle is None:
            failures += 1
            print(f"Missing golden outputs for {scenario.scenario_id}. Run tools/memory_proof_generate.py.")
            continue
        diff = diff_scenario(normalized, golden_bundle)
        report_text, report_json = build_report(
            scenario_id=scenario.scenario_id,
            scenario_name=scenario.name,
            invariants=invariants,
            diff=diff,
        )
        plain_text = build_plain_text(normalized["meta"])
        write_scenario_artifacts(
            root=output_dir,
            scenario_id=scenario.scenario_id,
            recall_steps=normalized["recall_steps"],
            write_steps=normalized["write_steps"],
            meta=normalized["meta"],
            plain_text=plain_text,
            report_text=report_text,
            report_json=report_json,
        )
        if not invariants.ok or not diff.ok:
            failures += 1
            print(report_text)
        else:
            print(f"Memory proof ok: {scenario.scenario_id}")
    return 1 if failures else 0


def _load_bundle(root: Path, scenario_id: str) -> dict | None:
    scenario_dir = root / scenario_id
    recall_path = scenario_dir / "recall_steps.json"
    write_path = scenario_dir / "write_steps.json"
    meta_path = scenario_dir / "meta.json"
    if not recall_path.exists() or not write_path.exists() or not meta_path.exists():
        return None
    return {
        "recall_steps": json.loads(recall_path.read_text(encoding="utf-8")),
        "write_steps": json.loads(write_path.read_text(encoding="utf-8")),
        "meta": json.loads(meta_path.read_text(encoding="utf-8")),
    }


if __name__ == "__main__":
    raise SystemExit(main())
