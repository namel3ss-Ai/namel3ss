from __future__ import annotations

import re
from pathlib import Path


def _license_file_from_pyproject(text: str) -> str | None:
    match = re.search(r'license\s*=\s*\{\s*file\s*=\s*"([^"]+)"\s*\}', text)
    if not match:
        return None
    return match.group(1)


def test_compliance_artifacts_exist_and_match() -> None:
    license_path = Path("LICENSE")
    notice_path = Path("NOTICE")
    compliance_doc = Path("docs/security/compliance.md")

    assert license_path.exists()
    assert license_path.read_text(encoding="utf-8").strip()
    assert notice_path.exists()
    notice_text = notice_path.read_text(encoding="utf-8")
    assert notice_text.strip()
    assert compliance_doc.exists()
    assert compliance_doc.read_text(encoding="utf-8").strip()

    pyproject_text = Path("pyproject.toml").read_text(encoding="utf-8")
    assert _license_file_from_pyproject(pyproject_text) == "LICENSE"

    for name in ["setuptools", "wheel", "pytest", "psycopg", "pymysql"]:
        assert name in notice_text
