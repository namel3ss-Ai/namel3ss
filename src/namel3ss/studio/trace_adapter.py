from __future__ import annotations

from namel3ss.production_contract import apply_trace_hash, normalize_traces


def normalize_action_response(payload: dict) -> dict:
    traces = payload.get("traces")
    if isinstance(traces, list):
        normalized = normalize_traces(traces)
        payload["traces"] = normalized
        contract = payload.get("contract")
        if isinstance(contract, dict) and isinstance(contract.get("traces"), list):
            contract["traces"] = normalized
        apply_trace_hash(payload)
    return payload


__all__ = ["normalize_action_response"]
