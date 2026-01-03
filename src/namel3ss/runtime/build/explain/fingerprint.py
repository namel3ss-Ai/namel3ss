from __future__ import annotations

import hashlib
from typing import Any, Dict, List

from namel3ss.utils.json_tools import dumps


def compute_build_id(
    *,
    api_version: str,
    source_fingerprint: str,
    guarantees: List[str],
    constraints: List[str],
    capabilities: Dict[str, Any],
) -> str:
    payload = {
        "api_version": api_version,
        "source_fingerprint": source_fingerprint,
        "guarantees": sorted(guarantees),
        "constraints": sorted(constraints),
        "capabilities": capabilities,
    }
    canonical = dumps(payload, sort_keys=True)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return digest


__all__ = ["compute_build_id"]
