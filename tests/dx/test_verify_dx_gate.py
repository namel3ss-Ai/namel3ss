from pathlib import Path

from namel3ss.governance.verify_dx import run_verify_dx


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_verify_dx_report_ok() -> None:
    report = run_verify_dx(project_root=_repo_root())
    assert report["ok"] is True
    dx = report["dx"]
    for key in [
        "silent_failure",
        "secret_leaks",
        "type_contract",
        "template_zero_setup",
        "studio_invariants",
    ]:
        assert dx[key]["status"] == "ok"
    serialized = str(report)
    assert "sk-" not in serialized
    assert "Bearer " not in serialized
