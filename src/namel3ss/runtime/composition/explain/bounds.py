from __future__ import annotations

API_VERSION = "composition"

MAX_CALLS = 50
MAX_PIPELINE_RUNS = 25
MAX_PIPELINE_STEPS = 120
MAX_ORCHESTRATIONS = 25
MAX_BRANCHES = 50
MAX_MERGE_DETAILS = 50


def _apply_limit(items: list[dict], limit: int) -> tuple[list[dict], bool]:
    if len(items) <= limit:
        return items, False
    return items[:limit], True


__all__ = [
    "API_VERSION",
    "MAX_CALLS",
    "MAX_PIPELINE_RUNS",
    "MAX_PIPELINE_STEPS",
    "MAX_ORCHESTRATIONS",
    "MAX_BRANCHES",
    "MAX_MERGE_DETAILS",
]
