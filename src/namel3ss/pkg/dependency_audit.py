from __future__ import annotations

import json
import os
from pathlib import Path


AUDIT_DB_ENV = "N3_DEP_AUDIT_DB"
DEFAULT_AUDIT_DB = Path(__file__).resolve().parents[3] / "resources" / "dependency_advisories_v1.json"


def load_audit_database() -> dict[str, object]:
    path_env = os.environ.get(AUDIT_DB_ENV, "").strip()
    path = Path(path_env) if path_env else DEFAULT_AUDIT_DB
    if not path.exists():
        return {"advisories": []}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"advisories": []}
    if not isinstance(payload, dict):
        return {"advisories": []}
    advisories = payload.get("advisories")
    if not isinstance(advisories, list):
        return {"advisories": []}
    return {"advisories": advisories}


def match_advisories(
    payload: dict[str, object],
    *,
    name: str,
    version: str,
    source: str,
) -> list[dict[str, object]]:
    advisories = payload.get("advisories") if isinstance(payload, dict) else None
    if not isinstance(advisories, list):
        return []
    matches: list[dict[str, object]] = []
    for raw in advisories:
        if not isinstance(raw, dict):
            continue
        adv_name = str(raw.get("name") or "").strip().lower()
        if adv_name != name.strip().lower():
            continue
        adv_source = str(raw.get("source") or "").strip().lower() or "any"
        if adv_source not in {"any", source.strip().lower()}:
            continue
        affected_versions = raw.get("affected_versions")
        if isinstance(affected_versions, list) and version not in {str(item) for item in affected_versions}:
            continue
        matches.append(
            {
                "name": name,
                "version": version,
                "source": source,
                "severity": str(raw.get("severity") or "medium"),
                "id": str(raw.get("id") or "unknown"),
                "description": str(raw.get("description") or ""),
                "url": str(raw.get("url") or ""),
            }
        )
    return matches


__all__ = ["load_audit_database", "match_advisories"]
