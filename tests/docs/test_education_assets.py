from __future__ import annotations

import re
from pathlib import Path

from namel3ss.utils.simple_yaml import parse_yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")


def _load_yaml(path: str) -> dict[str, object]:
    target = REPO_ROOT / path
    assert target.exists(), f"Missing education asset: {path}"
    payload = parse_yaml(target.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_education_catalog_is_deterministic_and_valid() -> None:
    payload = _load_yaml("docs/education/catalog.yaml")
    assert payload.get("version") == "1.0.0"
    courses = payload.get("courses")
    assert isinstance(courses, list) and courses

    ids: list[str] = []
    for course in courses:
        assert isinstance(course, dict)
        course_id = str(course.get("id", "")).strip()
        level = str(course.get("level", "")).strip()
        spec = str(course.get("requires_spec", "")).strip()
        modules = course.get("modules")
        assert course_id
        assert level in {"beginner", "intermediate", "advanced"}
        assert _SEMVER_RE.match(spec)
        assert isinstance(modules, list) and modules
        ids.append(course_id)

    assert ids == sorted(ids)
    assert len(ids) == len(set(ids))


def test_certifications_and_events_are_well_formed() -> None:
    certs = _load_yaml("docs/education/certifications.yaml")
    events = _load_yaml("docs/education/events.yaml")

    assert certs.get("version") == "1.0.0"
    cert_rows = certs.get("certifications")
    assert isinstance(cert_rows, list) and cert_rows
    for row in cert_rows:
        assert isinstance(row, dict)
        assert _SEMVER_RE.match(str(row.get("spec_version", "")).strip())
        exam = row.get("exam")
        assert isinstance(exam, dict)
        assert isinstance(exam.get("passing_score"), int)
        assert isinstance(exam.get("duration_minutes"), int)

    assert events.get("version") == "1.0.0"
    channels = events.get("community_channels")
    rows = events.get("events")
    assert isinstance(channels, list) and channels
    assert isinstance(rows, list) and rows
    ids = [str(row.get("id", "")).strip() for row in rows if isinstance(row, dict)]
    assert ids == sorted(ids)
