from __future__ import annotations

TRACE_VERSION = "2024-10-01"


class TraceEventType:
    AI_CALL_STARTED = "ai_call_started"
    AI_CALL_COMPLETED = "ai_call_completed"
    AI_CALL_FAILED = "ai_call_failed"
    TOOL_CALL_REQUESTED = "tool_call_requested"
    TOOL_CALL_COMPLETED = "tool_call_completed"
    TOOL_CALL_FAILED = "tool_call_failed"
    CAPABILITY_CHECK = "capability_check"
    MEMORY_RECALL = "memory_recall"
    MEMORY_WRITE = "memory_write"
    MEMORY_DENIED = "memory_denied"
    MEMORY_FORGET = "memory_forget"
    MEMORY_CONFLICT = "memory_conflict"
    MEMORY_BORDER_CHECK = "memory_border_check"
    MEMORY_PROMOTED = "memory_promoted"
    MEMORY_PROMOTION_DENIED = "memory_promotion_denied"
    MEMORY_PHASE_STARTED = "memory_phase_started"
    MEMORY_DELETED = "memory_deleted"
    MEMORY_PHASE_DIFF = "memory_phase_diff"
    MEMORY_EXPLANATION = "memory_explanation"
    MEMORY_LINKS = "memory_links"
    MEMORY_PATH = "memory_path"
    MEMORY_IMPACT = "memory_impact"
    MEMORY_CHANGE_PREVIEW = "memory_change_preview"
    MEMORY_TEAM_SUMMARY = "memory_team_summary"
    MEMORY_PROPOSED = "memory_proposed"
    MEMORY_APPROVED = "memory_approved"
    MEMORY_REJECTED = "memory_rejected"
    MEMORY_AGREEMENT_SUMMARY = "memory_agreement_summary"
    MEMORY_TRUST_CHECK = "memory_trust_check"
    MEMORY_APPROVAL_RECORDED = "memory_approval_recorded"
    MEMORY_TRUST_RULES = "memory_trust_rules"


__all__ = ["TRACE_VERSION", "TraceEventType"]
