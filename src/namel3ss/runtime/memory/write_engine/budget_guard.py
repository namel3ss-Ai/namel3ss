from __future__ import annotations


def budget_allows(
    budget_enforcer,
    *,
    store_key: str,
    space: str,
    owner: str,
    lane: str,
    phase,
    kind: str,
    incoming: int = 1,
) -> bool:
    if budget_enforcer is None:
        return True
    return budget_enforcer.allow_write(
        store_key=store_key,
        space=space,
        owner=owner,
        lane=lane,
        phase=phase,
        kind=kind,
        incoming=incoming,
    )


__all__ = ["budget_allows"]
