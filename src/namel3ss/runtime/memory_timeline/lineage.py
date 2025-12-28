from __future__ import annotations


def lineage_chain(start_id: str, *, replaced_by: dict[str, str] | None = None, limit: int = 20) -> list[str]:
    if not replaced_by:
        return [start_id]
    chain = [start_id]
    current = start_id
    while current in replaced_by and len(chain) < limit:
        current = replaced_by[current]
        chain.append(current)
    return chain


__all__ = ["lineage_chain"]
