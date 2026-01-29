import json
from pathlib import Path

from namel3ss.runtime.audit.builder import build_decision_model
from namel3ss.runtime.audit.report import build_audit_report


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "fixtures"


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def test_audit_report_includes_upload_lifecycle() -> None:
    payload = _load_fixture("audit_input_uploads.json")
    model = build_decision_model(
        state=payload.get("state"),
        traces=payload.get("traces"),
        project_root=None,
        app_path=None,
        policy_decl=None,
        identity=None,
        upload_id=None,
        query=None,
        secret_values=[],
    )
    report = build_audit_report(
        model,
        project_root=None,
        app_path=None,
        secret_values=[],
    )
    expected = _load_fixture("audit_report_uploads_golden.json")
    assert report == expected
