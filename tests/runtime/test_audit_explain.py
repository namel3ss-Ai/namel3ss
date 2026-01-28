import json
from pathlib import Path

from namel3ss.beta_lock.repo_clean import repo_dirty_entries
from namel3ss.runtime.audit.builder import build_decision_model
from namel3ss.runtime.audit.render_plain import render_audit
from namel3ss.runtime.audit.report import build_audit_report


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "fixtures"


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def _build_report() -> dict:
    payload = _load_fixture("audit_input.json")
    identity = {"subject": "user-SECRET_TOKEN", "roles": ["reviewer"], "permissions": []}
    secret_values = ["SECRET_TOKEN"]
    model = build_decision_model(
        state=payload.get("state"),
        traces=payload.get("traces"),
        project_root=None,
        app_path=None,
        policy_decl=None,
        identity=identity,
        upload_id=None,
        query="invoice",
        secret_values=secret_values,
    )
    return build_audit_report(
        model,
        project_root=None,
        app_path=None,
        secret_values=secret_values,
    )


def test_audit_report_matches_fixture() -> None:
    report = _build_report()
    expected = _load_fixture("audit_report_golden.json")
    assert report == expected


def test_audit_explain_is_deterministic() -> None:
    report_one = _build_report()
    report_two = _build_report()
    text_one = render_audit(report_one)
    text_two = render_audit(report_two)
    assert text_one == text_two


def test_audit_includes_decision_categories() -> None:
    report = _build_report()
    categories = {entry.get("category") for entry in report.get("decisions", []) if isinstance(entry, dict)}
    assert {"upload", "ingestion", "review", "policy", "retrieval"}.issubset(categories)


def test_audit_redacts_paths_and_secrets() -> None:
    report = _build_report()
    serialized = json.dumps(report, sort_keys=True)
    assert "SECRET_TOKEN" not in serialized
    assert "/Users/" not in serialized
    assert "<path>" in serialized
    assert "***REDACTED***" in serialized


def test_audit_does_not_dirty_repo() -> None:
    baseline = set(repo_dirty_entries(ROOT))
    _build_report()
    assert set(repo_dirty_entries(ROOT)) == baseline
