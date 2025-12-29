from __future__ import annotations

from .graph import Edge, ExplanationGraph, Node


def build_graph(proof_pack: dict) -> ExplanationGraph:
    payload = proof_pack.get("payload")
    events = _events_list(proof_pack)
    meta = proof_pack.get("meta") or {}
    proof = proof_pack.get("proof") or {}
    operation = _operation_kind(payload, events, meta)

    nodes: list[Node] = []
    edges: list[Edge] = []

    root_id = f"{operation}:1"
    root_title = "Memory recall" if operation == "recall" else "Memory write"
    nodes.append(
        Node(
            id=root_id,
            kind=operation,
            title=root_title,
            details={"summary": proof_pack.get("summary")},
        )
    )

    summary = _build_summary(operation, payload, meta, proof, events)

    item_nodes, item_edges = _build_item_nodes(operation, payload, root_id)
    nodes.extend(item_nodes)
    edges.extend(item_edges)

    phase_node, phase_edge = _build_phase_node(meta, proof, root_id)
    if phase_node:
        nodes.append(phase_node)
    if phase_edge:
        edges.append(phase_edge)

    cache_nodes, cache_edges = _build_cache_nodes(events, root_id)
    nodes.extend(cache_nodes)
    edges.extend(cache_edges)

    budget_nodes, budget_edges = _build_budget_nodes(events, root_id)
    nodes.extend(budget_nodes)
    edges.extend(budget_edges)

    decision_nodes, decision_edges, skip_nodes, skip_edges = _build_decision_nodes(events, root_id)
    nodes.extend(decision_nodes)
    edges.extend(decision_edges)
    nodes.extend(skip_nodes)
    edges.extend(skip_edges)

    return ExplanationGraph(nodes=nodes, edges=edges, summary=summary)


def _events_list(proof_pack: dict) -> list[dict]:
    events = proof_pack.get("events") or []
    return [event for event in events if isinstance(event, dict)]


def _operation_kind(payload: object, events: list[dict], meta: dict) -> str:
    if _has_event(events, "memory_write"):
        return "write"
    if isinstance(payload, list):
        return "write"
    if isinstance(payload, dict) and any(key in payload for key in ("short_term", "semantic", "profile")):
        return "recall"
    if meta.get("recall_counts") or meta.get("spaces_consulted"):
        return "recall"
    return "recall"


def _has_event(events: list[dict], event_type: str) -> bool:
    return any(event.get("type") == event_type for event in events)


def _build_summary(operation: str, payload: object, meta: dict, proof: dict, events: list[dict]) -> dict:
    counts = {"short_term": 0, "semantic": 0, "profile": 0}
    total = 0
    if operation == "recall" and isinstance(payload, dict):
        for kind in counts:
            entries = payload.get(kind, [])
            counts[kind] = len(entries) if isinstance(entries, list) else 0
        total = sum(counts.values())
    if operation == "write" and isinstance(payload, list):
        total = len(payload)
        for item in payload:
            kind = item.get("kind") if isinstance(item, dict) else None
            if kind in counts:
                counts[kind] += 1
    spaces = _spaces_consulted(meta, events)
    lanes = _lanes_consulted(events)
    phase_id = _phase_id(meta)
    phase_mode = proof.get("phase_mode") if isinstance(proof, dict) else None
    cache = _cache_summary(events)
    budgets = _budget_summary(events)
    return {
        "operation": operation,
        "total": int(total),
        "counts": counts,
        "spaces_consulted": spaces,
        "lanes_consulted": lanes,
        "phase_id": phase_id,
        "phase_mode": phase_mode,
        "cache_events": cache,
        "budget_events": budgets,
    }


def _spaces_consulted(meta: dict, events: list[dict]) -> list[str]:
    spaces = meta.get("spaces_consulted")
    if isinstance(spaces, list) and spaces:
        return [str(space) for space in spaces]
    found: list[str] = []
    for event in events:
        if event.get("type") != "memory_border_check":
            continue
        if event.get("action") != "read":
            continue
        if not event.get("allowed", False):
            continue
        space = event.get("from_space") or event.get("space")
        if space and space not in found:
            found.append(str(space))
    return found


def _lanes_consulted(events: list[dict]) -> list[str]:
    found: list[str] = []
    for event in events:
        if event.get("type") != "memory_border_check":
            continue
        if event.get("action") != "lane_read":
            continue
        if not event.get("allowed", False):
            continue
        lane = event.get("from_lane") or event.get("lane")
        if lane and lane not in found:
            found.append(str(lane))
    return found


def _phase_id(meta: dict) -> str | None:
    current = meta.get("current_phase")
    if isinstance(current, dict):
        phase_id = current.get("phase_id")
        if phase_id:
            return str(phase_id)
    return None


def _cache_summary(events: list[dict]) -> list[str]:
    hits = 0
    misses = 0
    for event in events:
        if event.get("type") == "memory_cache_hit":
            hits += 1
        elif event.get("type") == "memory_cache_miss":
            misses += 1
    parts: list[str] = []
    if hits:
        parts.append(f"hit:{hits}")
    if misses:
        parts.append(f"miss:{misses}")
    return parts


def _budget_summary(events: list[dict]) -> list[str]:
    entries: list[str] = []
    for event in events:
        if event.get("type") != "memory_budget":
            continue
        space = event.get("space")
        lane = event.get("lane")
        phase_id = event.get("phase_id")
        label = ":".join([str(value) for value in (space, lane, phase_id) if value])
        entries.append(label or "budget")
    return entries


def _build_item_nodes(operation: str, payload: object, root_id: str) -> tuple[list[Node], list[Edge]]:
    nodes: list[Node] = []
    edges: list[Edge] = []
    if operation == "recall" and isinstance(payload, dict):
        for kind in ("short_term", "semantic", "profile"):
            entries = payload.get(kind, [])
            if not isinstance(entries, list):
                continue
            for item in entries:
                node, edge = _item_node(item, kind=kind, root_id=root_id, note="recalled")
                nodes.append(node)
                edges.append(edge)
    if operation == "write" and isinstance(payload, list):
        for item in payload:
            node, edge = _item_node(item, kind="written", root_id=root_id, note="written")
            nodes.append(node)
            edges.append(edge)
    return nodes, edges


def _item_node(item: object, *, kind: str, root_id: str, note: str) -> tuple[Node, Edge]:
    item_dict = item if isinstance(item, dict) else {}
    memory_id = item_dict.get("id") or f"{kind}:unknown"
    node_id = f"item:{memory_id}"
    meta = item_dict.get("meta") if isinstance(item_dict.get("meta"), dict) else {}
    details = {
        "id": memory_id,
        "kind": item_dict.get("kind") or kind,
        "space": meta.get("space"),
        "lane": meta.get("lane"),
        "owner": meta.get("owner"),
        "phase_id": meta.get("phase_id"),
    }
    node = Node(id=node_id, kind="item", title=f"{details['kind']} item", details=details)
    edge = Edge(src=root_id, dst=node_id, kind="because", note=note)
    return node, edge


def _build_phase_node(meta: dict, proof: dict, root_id: str) -> tuple[Node | None, Edge | None]:
    phase = meta.get("current_phase")
    if not isinstance(phase, dict):
        return None, None
    phase_id = phase.get("phase_id")
    if not phase_id:
        return None, None
    details = dict(phase)
    if isinstance(proof, dict) and proof.get("phase_mode"):
        details["phase_mode"] = proof.get("phase_mode")
    node = Node(id=f"phase:{phase_id}", kind="phase", title=f"Phase {phase_id}", details=details)
    edge = Edge(src=root_id, dst=node.id, kind="because", note="phase policy applied")
    return node, edge


def _build_cache_nodes(events: list[dict], root_id: str) -> tuple[list[Node], list[Edge]]:
    nodes: list[Node] = []
    edges: list[Edge] = []
    for idx, event in enumerate(events, start=1):
        if event.get("type") not in {"memory_cache_hit", "memory_cache_miss"}:
            continue
        hit = event.get("type") == "memory_cache_hit"
        label = "hit" if hit else "miss"
        node_id = f"cache:{label}:{idx}"
        details = {
            "space": event.get("space"),
            "lane": event.get("lane"),
            "phase_id": event.get("phase_id"),
        }
        title = event.get("title") or f"Cache {label}"
        nodes.append(Node(id=node_id, kind="cache", title=str(title), details=details))
        edges.append(Edge(src=root_id, dst=node_id, kind="because", note="cache applied"))
    return nodes, edges


def _build_budget_nodes(events: list[dict], root_id: str) -> tuple[list[Node], list[Edge]]:
    nodes: list[Node] = []
    edges: list[Edge] = []
    for idx, event in enumerate(events, start=1):
        if event.get("type") != "memory_budget":
            continue
        node_id = f"budget:{idx}"
        details = {
            "space": event.get("space"),
            "lane": event.get("lane"),
            "phase_id": event.get("phase_id"),
        }
        title = event.get("title") or "Memory budget"
        nodes.append(Node(id=node_id, kind="budget", title=str(title), details=details))
        edges.append(Edge(src=root_id, dst=node_id, kind="because", note="budget applied"))
    return nodes, edges


def _build_decision_nodes(
    events: list[dict],
    root_id: str,
) -> tuple[list[Node], list[Edge], list[Node], list[Edge]]:
    decisions: list[Node] = []
    decision_edges: list[Edge] = []
    skips: list[Node] = []
    skip_edges: list[Edge] = []
    for idx, event in enumerate(events, start=1):
        event_type = event.get("type")
        if event_type == "memory_border_check":
            action = event.get("action")
            allowed = bool(event.get("allowed", False))
            space = event.get("from_space") or event.get("space")
            lane = event.get("from_lane") or event.get("lane")
            reason = event.get("reason") or "policy"
            label = _border_label(action, space, lane)
            if allowed:
                node_id = f"decision:{action}:{idx}"
                title = f"Allowed {label}"
                node = Node(id=node_id, kind="decision", title=title, details={"reason": reason})
                decisions.append(node)
                decision_edges.append(Edge(src=root_id, dst=node_id, kind="because", note=str(reason)))
            else:
                node_id = f"skip:{action}:{idx}"
                title = f"Denied {label}"
                node = Node(id=node_id, kind="skip", title=title, details={"reason": reason})
                skips.append(node)
                skip_edges.append(Edge(src=root_id, dst=node_id, kind="skipped_because", note=str(reason)))
            continue
        if event_type in {"memory_denied", "memory_promotion_denied", "memory_compaction"}:
            reason = event.get("reason") or event.get("title") or "policy"
            node_id = f"skip:{event_type}:{idx}"
            title = _skip_title(event_type)
            skips.append(Node(id=node_id, kind="skip", title=title, details={"reason": reason}))
            skip_edges.append(Edge(src=root_id, dst=node_id, kind="skipped_because", note=str(reason)))
    return decisions, decision_edges, skips, skip_edges


def _border_label(action: object, space: object, lane: object) -> str:
    label = str(action or "read")
    parts = []
    if space:
        parts.append(str(space))
    if lane:
        parts.append(str(lane))
    if parts:
        return f"{label} ({' / '.join(parts)})"
    return label


def _skip_title(event_type: str) -> str:
    if event_type == "memory_denied":
        return "Denied memory write"
    if event_type == "memory_promotion_denied":
        return "Denied memory promotion"
    if event_type == "memory_compaction":
        return "Memory compaction"
    return "Skipped"


__all__ = ["build_graph"]
