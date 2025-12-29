from __future__ import annotations

import json
from pathlib import Path

from namel3ss.errors.runtime.builder import build_error_pack
from namel3ss.errors.runtime.model import RuntimeWhere
from namel3ss.runtime.boundary import attach_project_root


def _build_pack(tmp_path: Path) -> tuple[str, str]:
    err = ValueError("boom")
    attach_project_root(err, tmp_path)
    where = RuntimeWhere(flow_name="demo", statement_kind="set", statement_index=1, line=2, column=3)
    pack = build_error_pack(boundary="engine", err=err, where=where)
    plain = (tmp_path / ".namel3ss" / "errors" / "last.plain").read_text(encoding="utf-8")
    return pack.error.error_id, plain


def test_error_pack_deterministic(tmp_path: Path) -> None:
    first_id, first_plain = _build_pack(tmp_path)
    second_id, second_plain = _build_pack(tmp_path)
    assert first_id == second_id
    assert first_plain == second_plain


def test_error_redaction(tmp_path: Path, monkeypatch) -> None:
    secret = "supersecretkey"
    monkeypatch.setenv("NAMEL3SS_OPENAI_API_KEY", secret)
    err = ValueError(f"bad key: {secret}")
    attach_project_root(err, tmp_path)
    where = RuntimeWhere(flow_name="demo", statement_kind=None, statement_index=None, line=None, column=None)
    pack = build_error_pack(
        boundary="engine",
        err=err,
        where=where,
        traces=[{"type": "runtime_error", "detail": secret}],
    )
    payload = json.loads((tmp_path / ".namel3ss" / "errors" / "last.json").read_text(encoding="utf-8"))
    assert "***REDACTED***" in pack.error.raw_message
    assert secret not in json.dumps(payload)
