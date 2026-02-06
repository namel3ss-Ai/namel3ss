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
    "console": "console",
    "lint": "lint",
    "graph": "graph",
    "exports": "exports",
    "run": "run",
    "dev": "dev",
    "preview": "preview",
    "start": "start",
    "test": "test",
    "editor": "editor",
    "reserved": "reserved",
    "icons": "icons",
    "init": "init",
    "scaffold": "scaffold",
    "package": "package",
    "tutorial": "tutorial",
    "lsp": "lsp",
    # Data/persistence
    "data": "data",
    "persist": "data",
    # Packages
    "pkg": "pkg",
    # Docs and SDK
    "docs": "docs",
    "sdk": "sdk",
    "metrics": "metrics",
    "secret": "secret",
    "policy": "policy",
    "trace": "trace",
    "debug": "debug",
    "replay": "replay",
    "export": "export",
    "observability": "observability",
    "ast": "ast",
    "type": "type",
    "schema": "schema",
    "concurrency": "concurrency",
    "trigger": "trigger",
    "prompts": "prompts",
    "conventions": "conventions",
    "formats": "formats",
    "plugin": "plugin",
    "feedback": "feedback",
    "dataset": "dataset",
    "train": "train",
    "retrain": "retrain",
    "model": "model",
    "models": "models",
    "tenant": "tenant",
    "federation": "federation",
    "cluster": "cluster",
    "marketplace": "marketplace",
    "quality": "quality",
    "mlops": "mlops",
    "new": "new",
}


def canonical_command(raw: str) -> str:
    return ALIAS_MAP.get(raw.lower(), raw.lower())


__all__ = ["ALIAS_MAP", "canonical_command"]
