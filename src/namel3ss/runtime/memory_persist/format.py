from __future__ import annotations

from dataclasses import asdict
from typing import Any

from namel3ss.errors.base import Namel3ssError
from namel3ss.runtime.memory.contract import MemoryItem, validate_memory_item, validate_memory_kind, validate_scope
from namel3ss.runtime.memory_agreement.model import Proposal
from namel3ss.runtime.memory_budget.model import BudgetConfig
from namel3ss.runtime.memory_handoff.model import HandoffPacket
from namel3ss.runtime.memory_timeline.phase import PhaseInfo
from namel3ss.runtime.memory_timeline.snapshot import SnapshotItem
from namel3ss.runtime.memory_trust.model import TrustRules
from namel3ss.secrets.redaction import redact_payload

MEMORY_STORE_VERSION = "memory_store_v1"


def encode_memory_item(item: MemoryItem | dict, *, secret_values: list[str] | None = None) -> dict:
    data = item.as_dict() if isinstance(item, MemoryItem) else dict(item)
    if secret_values:
        data = redact_payload(data, secret_values)  # type: ignore[assignment]
    return data


def decode_memory_item(data: dict) -> MemoryItem:
    validate_memory_item(data)
    kind = validate_memory_kind(data.get("kind"))
    scope = validate_scope(str(data.get("scope")))
    meta = data.get("meta") if isinstance(data.get("meta"), dict) else {}
    return MemoryItem(
        id=str(data.get("id")),
        kind=kind,
        text=str(data.get("text")),
        source=str(data.get("source")),
        created_at=int(data.get("created_at")),
        importance=int(data.get("importance")),
        scope=scope,
        meta=dict(meta),
    )


def encode_phase_info(info: PhaseInfo) -> dict:
    payload = {
        "phase_id": info.phase_id,
        "phase_index": int(info.phase_index),
        "started_at": int(info.started_at),
        "reason": info.reason,
    }
    if info.name:
        payload["name"] = info.name
    return payload


def decode_phase_info(data: dict) -> PhaseInfo:
    if not isinstance(data, dict):
        raise Namel3ssError("Phase info must be a mapping.")
    return PhaseInfo(
        phase_id=str(data.get("phase_id")),
        phase_index=int(data.get("phase_index")),
        started_at=int(data.get("started_at")),
        reason=str(data.get("reason")),
        name=str(data.get("name")) if data.get("name") else None,
    )


def encode_snapshot_item(item: SnapshotItem) -> dict:
    return {
        "memory_id": item.memory_id,
        "kind": item.kind,
        "dedupe_key": item.dedupe_key,
    }


def decode_snapshot_item(data: dict) -> SnapshotItem:
    if not isinstance(data, dict):
        raise Namel3ssError("Snapshot item must be a mapping.")
    return SnapshotItem(
        memory_id=str(data.get("memory_id")),
        kind=str(data.get("kind")),
        dedupe_key=str(data.get("dedupe_key")) if data.get("dedupe_key") else None,
    )


def encode_budget_config(config: BudgetConfig) -> dict:
    return asdict(config)


def decode_budget_config(data: dict) -> BudgetConfig:
    if not isinstance(data, dict):
        raise Namel3ssError("Budget config must be a mapping.")
    return BudgetConfig(
        space=str(data.get("space", "any")),
        lane=str(data.get("lane", "any")),
        phase=str(data.get("phase", "any")),
        owner=str(data.get("owner", "any")),
        max_items_short_term=_optional_int(data.get("max_items_short_term")),
        max_items_semantic=_optional_int(data.get("max_items_semantic")),
        max_items_profile=_optional_int(data.get("max_items_profile")),
        max_items_team=_optional_int(data.get("max_items_team")),
        max_items_agent=_optional_int(data.get("max_items_agent")),
        max_links_per_item=_optional_int(data.get("max_links_per_item")),
        max_phases_per_lane=_optional_int(data.get("max_phases_per_lane")),
        cache_enabled=bool(data.get("cache_enabled", True)),
        cache_max_entries=int(data.get("cache_max_entries", 0) or 0),
        compaction_enabled=bool(data.get("compaction_enabled", True)),
    )


def encode_trust_rules(rules: TrustRules | None) -> dict | None:
    if rules is None:
        return None
    return rules.as_dict()


def decode_trust_rules(data: dict | None) -> TrustRules | None:
    if data is None:
        return None
    if not isinstance(data, dict):
        raise Namel3ssError("Trust rules must be a mapping.")
    return TrustRules(
        who_can_propose=str(data.get("who_can_propose")),
        who_can_approve=str(data.get("who_can_approve")),
        who_can_reject=str(data.get("who_can_reject")),
        approval_count_required=int(data.get("approval_count_required", 1)),
        owner_override=bool(data.get("owner_override", True)),
    )


def encode_proposal(proposal: Proposal, *, secret_values: list[str] | None = None) -> dict:
    return {
        "proposal_id": proposal.proposal_id,
        "memory_item": encode_memory_item(proposal.memory_item, secret_values=secret_values),
        "team_id": proposal.team_id,
        "phase_id": proposal.phase_id,
        "status": proposal.status,
        "proposed_by": proposal.proposed_by,
        "proposed_at": int(proposal.proposed_at),
        "approvals": list(proposal.approvals),
        "approval_count_required": int(proposal.approval_count_required),
        "owner_override": bool(proposal.owner_override),
        "reason_code": proposal.reason_code,
        "ai_profile": proposal.ai_profile,
    }


def decode_proposal(data: dict) -> Proposal:
    if not isinstance(data, dict):
        raise Namel3ssError("Proposal must be a mapping.")
    return Proposal(
        proposal_id=str(data.get("proposal_id")),
        memory_item=decode_memory_item(_require_mapping(data.get("memory_item"))),
        team_id=str(data.get("team_id")),
        phase_id=str(data.get("phase_id")),
        status=str(data.get("status")),
        proposed_by=str(data.get("proposed_by")),
        proposed_at=int(data.get("proposed_at")),
        approvals=list(data.get("approvals") or []),
        approval_count_required=int(data.get("approval_count_required", 1)),
        owner_override=bool(data.get("owner_override", True)),
        reason_code=str(data.get("reason_code")) if data.get("reason_code") else None,
        ai_profile=str(data.get("ai_profile")) if data.get("ai_profile") else None,
    )


def encode_handoff_packet(packet: HandoffPacket) -> dict:
    return {
        "packet_id": packet.packet_id,
        "from_agent_id": packet.from_agent_id,
        "to_agent_id": packet.to_agent_id,
        "team_id": packet.team_id,
        "space": packet.space,
        "phase_id": packet.phase_id,
        "created_by": packet.created_by,
        "created_at": int(packet.created_at),
        "items": list(packet.items),
        "summary_lines": list(packet.summary_lines),
        "status": packet.status,
    }


def decode_handoff_packet(data: dict) -> HandoffPacket:
    if not isinstance(data, dict):
        raise Namel3ssError("Handoff packet must be a mapping.")
    return HandoffPacket(
        packet_id=str(data.get("packet_id")),
        from_agent_id=str(data.get("from_agent_id")),
        to_agent_id=str(data.get("to_agent_id")),
        team_id=str(data.get("team_id")),
        space=str(data.get("space")),
        phase_id=str(data.get("phase_id")),
        created_by=str(data.get("created_by")),
        created_at=int(data.get("created_at")),
        items=list(data.get("items") or []),
        summary_lines=list(data.get("summary_lines") or []),
        status=str(data.get("status")),
    )


def encode_cache_value(value: Any, *, secret_values: list[str] | None = None) -> Any:
    if isinstance(value, MemoryItem):
        return encode_memory_item(value, secret_values=secret_values)
    if isinstance(value, dict):
        payload = {key: encode_cache_value(val, secret_values=secret_values) for key, val in value.items()}
        if secret_values:
            payload = redact_payload(payload, secret_values)  # type: ignore[assignment]
        return payload
    if isinstance(value, list):
        return [encode_cache_value(entry, secret_values=secret_values) for entry in value]
    if isinstance(value, tuple):
        return [encode_cache_value(entry, secret_values=secret_values) for entry in value]
    if secret_values and isinstance(value, str):
        return redact_payload(value, secret_values)
    return value


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    return int(value)


def _require_mapping(value: object) -> dict:
    if not isinstance(value, dict):
        raise Namel3ssError("Snapshot section is missing required fields.")
    return value


__all__ = [
    "MEMORY_STORE_VERSION",
    "decode_budget_config",
    "decode_handoff_packet",
    "decode_memory_item",
    "decode_phase_info",
    "decode_proposal",
    "decode_snapshot_item",
    "decode_trust_rules",
    "encode_budget_config",
    "encode_cache_value",
    "encode_handoff_packet",
    "encode_memory_item",
    "encode_phase_info",
    "encode_proposal",
    "encode_snapshot_item",
    "encode_trust_rules",
]
