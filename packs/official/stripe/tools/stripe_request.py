from __future__ import annotations


def run(payload):
    if not isinstance(payload, dict):
        raise ValueError("payload must be an object")
    stub = payload.get("stub_response")
    if stub is not None:
        if not isinstance(stub, dict):
            raise ValueError("payload.stub_response must be an object")
        return {"ok": True, "stub": True, "response": stub}
    return {
        "ok": False,
        "error": "Stripe pack is a stub. Provide stub_response for deterministic output.",
    }
