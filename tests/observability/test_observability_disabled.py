from __future__ import annotations

import json
from pathlib import Path

from namel3ss.cli.explain_mode import build_explain_payload


APP_SOURCE = '''spec is "1.0"

flow "demo":
  return "ok"
'''

PROOF_ID = "proof-test"
BUILD_ID = "build-test"


def _write_app(tmp_path: Path) -> Path:
    path = tmp_path / "app.ai"
    path.write_text(APP_SOURCE, encoding="utf-8")
    return path


def _write_proof(tmp_path: Path) -> None:
    root = tmp_path / ".namel3ss"
    proofs = root / "proofs"
    proofs.mkdir(parents=True, exist_ok=True)
    proof_payload = {
        "persistence": {"target": "memory", "descriptor": None},
        "identity": {
            "requires": {"flows": [], "pages": [], "flow_count": 0, "page_count": 0},
            "tenant_scoping": {"records": [], "count": 0},
        },
        "capsules": {"modules": []},
        "governance": {"status": "unknown", "checks": []},
    }
    (proofs / f"{PROOF_ID}.json").write_text(
        json.dumps(proof_payload, sort_keys=True, indent=2),
        encoding="utf-8",
    )
    (root / "active_proof.json").write_text(
        json.dumps({"proof_id": PROOF_ID, "target": "local", "build_id": BUILD_ID}, sort_keys=True, indent=2),
        encoding="utf-8",
    )


def test_explain_disabled_matches_golden(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("N3_OBSERVABILITY", raising=False)
    app_file = _write_app(tmp_path)
    _write_proof(tmp_path)
    payload = build_explain_payload(app_file, include_observability=False)
    expected_path = Path("tests/fixtures/observability/explain_disabled.json")
    expected = json.loads(expected_path.read_text(encoding="utf-8"))
    assert payload == expected
    assert "observability" not in payload
