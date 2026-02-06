from __future__ import annotations

from pathlib import Path

from namel3ss.governance.audit import list_audit_entries, record_audit_entry


def _write_app(tmp_path: Path) -> Path:
    app_path = tmp_path / "app.ai"
    app_path.write_text('spec is "1.0"\n\nflow "demo":\n  return "ok"\n', encoding="utf-8")
    return app_path


def test_audit_retention_and_anonymization_are_applied(tmp_path: Path) -> None:
    app_path = _write_app(tmp_path)
    (tmp_path / "retention.yaml").write_text(
        (
            'version: "1.0"\n'
            "records:\n"
            "  orders:\n"
            "    retention_days: 30\n"
            "    anonymize_fields:\n"
            "      - customer_email\n"
            "audit:\n"
            "  enabled: true\n"
            "  retention_days: 2\n"
        ),
        encoding="utf-8",
    )

    for idx in range(1, 4):
        record_audit_entry(
            project_root=tmp_path,
            app_path=app_path,
            user="alice",
            action="records.update",
            resource=f"orders/{idx}",
            status="success",
            details={
                "customer_email": f"user{idx}@example.com",
                "order_id": str(idx),
            },
        )

    rows = list_audit_entries(tmp_path, app_path)
    assert [row["timestamp"] for row in rows] == [2, 3]
    assert all(row["details"]["customer_email"] == "[REDACTED]" for row in rows)
    assert [row["details"]["order_id"] for row in rows] == ["2", "3"]
