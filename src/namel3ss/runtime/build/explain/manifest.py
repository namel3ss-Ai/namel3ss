from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass(frozen=True)
class BuildManifest:
    api_version: str
    build_id: str
    created_at: str
    project_root: str
    app_path: str
    inputs: Dict[str, Any]
    guarantees: List[str]
    constraints: List[str]
    capabilities: Dict[str, Any]
    components: Dict[str, Any]
    changes: Dict[str, Any] | None
    notes: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "api_version": self.api_version,
            "build_id": self.build_id,
            "created_at": self.created_at,
            "project_root": self.project_root,
            "app_path": self.app_path,
            "inputs": self.inputs,
            "guarantees": list(self.guarantees),
            "constraints": list(self.constraints),
            "capabilities": self.capabilities,
            "components": self.components,
            "changes": self.changes,
            "notes": list(self.notes),
        }


__all__ = ["BuildManifest"]
