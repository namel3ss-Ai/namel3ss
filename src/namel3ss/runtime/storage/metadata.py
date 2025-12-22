from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PersistenceMetadata:
    enabled: bool
    kind: str
    path: str | None
    schema_version: int | None
