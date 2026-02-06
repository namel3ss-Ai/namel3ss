from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def _read(path: str) -> str:
    target = REPO_ROOT / path
    assert target.exists(), f"Missing required governance file: {path}"
    return target.read_text(encoding="utf-8")


def test_governance_documents_exist_with_required_sections() -> None:
    governance = _read("GOVERNANCE.md")
    rfc_process = _read("RFC_PROCESS.md")
    conduct = _read("CODE_OF_CONDUCT.md")
    decisions = _read("DECISIONS.md")

    assert "Language Steering Committee" in governance
    assert "Voting model" in governance
    assert "Language change policy" in governance

    assert "Open an RFC" in rfc_process
    assert "Committee review" in rfc_process
    assert "Implementation gate" in rfc_process

    assert "Expected behavior" in conduct
    assert "Unacceptable behavior" in conduct
    assert "Enforcement" in conduct

    assert "Decisions Log" in decisions
    assert "D-0001" in decisions
    assert "rfc_id" in decisions


def test_community_docs_link_stewardship_assets() -> None:
    page = _read("docs/community-stewardship.md")
    assert "spec/grammar/v1.0.0/namel3ss.grammar" in page
    assert "GOVERNANCE.md" in page
    assert "docs/education/catalog.yaml" in page
