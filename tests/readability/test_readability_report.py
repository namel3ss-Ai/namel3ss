from __future__ import annotations

import json
import re
from pathlib import Path

from namel3ss.readability.analyze import analyze_files, render_json, render_text


def _resolve_reference_paths() -> list[Path]:
    references = [
        Path("src/namel3ss/templates/operations_dashboard/app.ai"),
        Path("src/namel3ss/templates/onboarding/app.ai"),
    ]
    resolved: list[Path] = []
    for path in references:
        if path.exists():
            resolved.append(path)
            continue
        resolved.append(path)
    return resolved


def test_readability_json_is_deterministic_and_sorted() -> None:
    target = Path("src/namel3ss/templates/operations_dashboard/app.ai")
    report_one = analyze_files([target], analyzed_path="operations_dashboard_template")
    json_one = render_json(report_one)
    text_one = render_text(report_one)
    report_two = analyze_files([target], analyzed_path="operations_dashboard_template")
    json_two = render_json(report_two)
    text_two = render_text(report_two)
    assert json_one == json_two
    assert text_one == text_two
    assert json_one == json.dumps(json.loads(json_one), indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    _assert_no_timestamps(json_one)
    _assert_no_timestamps(text_one)


def test_readability_report_includes_reference_targets() -> None:
    reference_files = _resolve_reference_paths()
    report = analyze_files(reference_files, analyzed_path="reference_targets")
    payload = json.loads(render_json(report))

    for key in [
        "schema_version",
        "analyzed_path",
        "score_formula",
        "score_weights",
        "file_count",
        "flow_count",
        "files",
    ]:
        assert key in payload

    file_paths = [entry["path"] for entry in payload["files"]]
    for ref in reference_files:
        expected_suffix = ref.as_posix()
        assert any(path.endswith(expected_suffix) for path in file_paths)

    sample_file = payload["files"][0]
    for key in [
        "path",
        "flow_count",
        "record_constraints_must",
        "ui_button_bindings_total",
        "ui_button_bindings",
        "flows",
        "top_offenders",
    ]:
        assert key in sample_file
    _assert_sorted_offenders(sample_file["top_offenders"])
    if sample_file["flows"]:
        sample_flow = sample_file["flows"][0]
        for key in ["name", "statement_count", "plumbing", "intent", "complexity", "scorecard", "top_offenders"]:
            assert key in sample_flow
        assert "plumbing_ratio" in sample_flow
        assert "score_inputs" in sample_flow["scorecard"]
        assert "record_constraints_must" in sample_flow["intent"]
        _assert_sorted_offenders(sample_flow["top_offenders"])


def test_readability_text_contains_headings() -> None:
    target = Path("src/namel3ss/templates/operations_dashboard/app.ai")
    report = analyze_files([target], analyzed_path="operations_dashboard_template")
    text = render_text(report)
    assert "Top offenders" in text
    assert "Roadmap mapping" in text
    assert "heatline:" in text
    _assert_no_timestamps(text)


def _assert_sorted_offenders(offenders: list[dict]) -> None:
    pairs = [(item["name"], item["count"]) for item in offenders]
    expected = sorted(pairs, key=lambda item: (-item[1], item[0]))
    assert pairs == expected


def _assert_no_timestamps(text: str) -> None:
    patterns = [
        re.compile(r"\\d{4}-\\d{2}-\\d{2}"),
        re.compile(r"\\d{2}:\\d{2}:\\d{2}"),
    ]
    for pattern in patterns:
        assert pattern.search(text) is None
