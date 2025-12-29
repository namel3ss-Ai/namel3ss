from __future__ import annotations

from namel3ss.graduation.capabilities import CATEGORY_ORDER, STATUS_ORDER, capabilities


def build_capability_matrix() -> dict:
    items = [_capability_payload(cap) for cap in capabilities()]
    items = sorted(items, key=_sort_key)
    summary = _build_summary(items)
    return {
        "summary": summary,
        "capabilities": items,
    }


def _capability_payload(cap) -> dict:
    return {
        "id": cap.id,
        "title": cap.title,
        "category": cap.category,
        "status": cap.status,
        "proofs": list(cap.proofs),
        "tests": list(cap.tests),
        "examples": list(cap.examples),
    }


def _sort_key(item: dict) -> tuple[int, str, str]:
    category = item.get("category") or ""
    try:
        category_index = CATEGORY_ORDER.index(category)
    except ValueError:
        category_index = len(CATEGORY_ORDER)
    return (category_index, category, str(item.get("id") or ""))


def _build_summary(items: list[dict]) -> dict:
    total = len(items)
    status_counts = {status: 0 for status in STATUS_ORDER}
    category_counts = {category: 0 for category in CATEGORY_ORDER}
    for item in items:
        status = item.get("status")
        if status in status_counts:
            status_counts[status] += 1
        category = item.get("category")
        if category in category_counts:
            category_counts[category] += 1
        elif category:
            category_counts[category] = category_counts.get(category, 0) + 1
    status_list = [
        {"status": status, "count": status_counts.get(status, 0)} for status in STATUS_ORDER
    ]
    category_list = [
        {"category": category, "count": category_counts.get(category, 0)}
        for category in CATEGORY_ORDER
        if category_counts.get(category, 0) > 0
    ]
    for category in sorted(category_counts.keys()):
        if category in CATEGORY_ORDER:
            continue
        count = category_counts.get(category, 0)
        if count:
            category_list.append({"category": category, "count": count})
    return {
        "total": total,
        "by_status": status_list,
        "by_category": category_list,
    }


__all__ = ["build_capability_matrix"]
