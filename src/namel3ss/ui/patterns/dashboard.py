from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re

from namel3ss.errors.base import Namel3ssError


@dataclass(frozen=True)
class DashboardPatternConfig:
    name: str = "metrics_dashboard"
    title: str = "Metrics Dashboard"
    metric_labels: tuple[str, ...] = ("Latency", "Error Rate", "Throughput", "Cost")
    columns: int = 2


def build_dashboard_pattern(config: DashboardPatternConfig | None = None) -> dict[str, object]:
    resolved = config or DashboardPatternConfig()
    if resolved.columns < 1:
        raise Namel3ssError("dashboard columns must be at least 1.")
    if not resolved.metric_labels:
        raise Namel3ssError("dashboard pattern requires at least one metric label.")
    if any(not isinstance(label, str) or not label.strip() for label in resolved.metric_labels):
        raise Namel3ssError("dashboard metric labels must be non-empty text values.")

    slug = _slugify(resolved.name)
    ids = _pattern_ids(slug)
    cards: list[dict[str, object]] = []
    for index, label in enumerate(resolved.metric_labels):
        card_id = _stable_id(slug, "component.card", (0, 0, index))
        text_id = _stable_id(slug, "component.literal", (0, 0, index, 0))
        cards.append(
            {
                "type": "component.card",
                "id": card_id,
                "name": label,
                "expandable": False,
                "collapsed": False,
                "children": [
                    {
                        "type": "component.literal",
                        "id": text_id,
                        "text": f"{label}: --",
                        "bindings": {"on_click": None, "keyboard_shortcut": None, "selected_item": None},
                        "line": 0,
                        "column": 0,
                    }
                ],
                "bindings": {"on_click": None, "keyboard_shortcut": None, "selected_item": None},
                "line": 0,
                "column": 0,
            }
        )

    return {
        "pattern": "dashboard",
        "name": resolved.name,
        "title": resolved.title,
        "state": [],
        "layout": [
            {
                "type": "layout.main",
                "id": ids["main"],
                "bindings": {"on_click": None, "keyboard_shortcut": None, "selected_item": None},
                "children": [
                    {
                        "type": "layout.scroll_area",
                        "id": ids["scroll"],
                        "axis": "vertical",
                        "bindings": {"on_click": None, "keyboard_shortcut": None, "selected_item": None},
                        "children": [
                            {
                                "type": "layout.grid",
                                "id": ids["grid"],
                                "columns": resolved.columns,
                                "children": cards,
                                "line": 0,
                                "column": 0,
                            }
                        ],
                        "line": 0,
                        "column": 0,
                    }
                ],
                "line": 0,
                "column": 0,
            }
        ],
        "actions": {},
    }


def _pattern_ids(slug: str) -> dict[str, str]:
    return {
        "main": _stable_id(slug, "layout.main", (0,)),
        "scroll": _stable_id(slug, "layout.scroll_area", (0, 0)),
        "grid": _stable_id(slug, "layout.grid", (0, 0, 0)),
    }


def _stable_id(slug: str, kind: str, path: tuple[int, ...]) -> str:
    payload = f"{slug}|{kind}|{'.'.join(str(part) for part in path)}"
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]
    return f"pattern.{slug}.{kind.replace('.', '_')}.{digest}"


def _slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "_", value.strip().lower())
    result = cleaned.strip("_")
    return result or "metrics_dashboard"


__all__ = ["DashboardPatternConfig", "build_dashboard_pattern"]
