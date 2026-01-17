from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from namel3ss.runtime.memory.proof import (
    build_plain_text,
    build_report,
    check_invariants,
    list_scenario_paths,
    load_scenario,
    normalize_meta,
    normalize_recall_steps,
    normalize_write_steps,
    write_scenario_artifacts,
)
from namel3ss.runtime.memory.proof.diff import DiffResult
from namel3ss.runtime.memory.proof.runner import run_scenario


def main() -> int:
    scenarios_dir = ROOT / "tests" / "memory_proof" / "scenarios"
    output_dir = ROOT / ".namel3ss" / "memory_proof" / "output"
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
        diff = DiffResult(ok=True, entries=[])
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
        write_scenario_artifacts(
            root=golden_dir,
            scenario_id=scenario.scenario_id,
            recall_steps=normalized["recall_steps"],
            write_steps=normalized["write_steps"],
            meta=normalized["meta"],
            plain_text=plain_text,
            report_text=report_text,
            report_json=report_json,
        )
        if not invariants.ok:
            failures += 1
            print(report_text)
        else:
            print(f"Generated memory proof: {scenario.scenario_id}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
