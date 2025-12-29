from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProofPack:
    ok: bool
    api_version: str
    payload: object
    events: list[dict]
    meta: dict
    proof: dict
    summary: str

    def as_dict(self) -> dict:
        return {
            "ok": self.ok,
            "api_version": self.api_version,
            "payload": self.payload,
            "events": list(self.events),
            "meta": dict(self.meta),
            "proof": dict(self.proof),
            "summary": self.summary,
        }


__all__ = ["ProofPack"]
