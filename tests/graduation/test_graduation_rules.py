from pathlib import Path

from namel3ss.graduation.matrix import build_capability_matrix
from namel3ss.graduation.render import render_graduation_lines, render_matrix_lines, render_summary_lines
from namel3ss.graduation.rules import STABILITY_CHECKS, STABILITY_PROMISES, evaluate_graduation
from namel3ss.spec_freeze.contracts.rules import has_bracket_chars


def test_graduation_rules() -> None:
    matrix = build_capability_matrix()
    report = evaluate_graduation(matrix)
    assert report.ai_language_ready is True
    assert report.beta_ready is False


def test_graduation_render_lines_bracketless() -> None:
    matrix = build_capability_matrix()
    report = evaluate_graduation(matrix)
    lines = render_summary_lines(matrix) + render_matrix_lines(matrix) + render_graduation_lines(report)
    for line in lines:
        assert not has_bracket_chars(line)


def test_stability_checks_exist() -> None:
    assert STABILITY_PROMISES
    for check in STABILITY_CHECKS:
        assert Path(check).exists()
