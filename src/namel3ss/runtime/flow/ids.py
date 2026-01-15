from __future__ import annotations

from namel3ss.ui.manifest.canonical import _slugify


def flow_id(flow_name: str) -> str:
    slug = _slugify(flow_name) or "flow"
    return f"flow:{slug}"


def flow_step_id(flow_name: str, step_kind: str, ordinal: int) -> str:
    base = flow_id(flow_name)
    kind = _slugify(step_kind) or step_kind
    return f"{base}.{kind}.{ordinal:02d}"


__all__ = ["flow_id", "flow_step_id"]
