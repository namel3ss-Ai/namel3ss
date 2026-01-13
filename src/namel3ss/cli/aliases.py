from __future__ import annotations

from typing import Dict

# Central alias table. Keys are accepted command words; values are canonical names.
ALIAS_MAP: Dict[str, str] = {
    # Phase 5 targets
    "pack": "pack",
    "build": "pack",
    "ship": "ship",
    "promote": "ship",
    "where": "where",
    "status": "status",
    # Core app commands
    "fmt": "fmt",
    "format": "fmt",
    "check": "check",
    "ui": "ui",
    "actions": "actions",
    "studio": "studio",
    "lint": "lint",
    "graph": "graph",
    "exports": "exports",
    "run": "run",
    "test": "test",
    "editor": "editor",
    "init": "new",
    # Data/persistence
    "data": "data",
    "persist": "data",
    # Packages
    "pkg": "pkg",
}


def canonical_command(raw: str) -> str:
    return ALIAS_MAP.get(raw.lower(), raw.lower())


__all__ = ["ALIAS_MAP", "canonical_command"]
