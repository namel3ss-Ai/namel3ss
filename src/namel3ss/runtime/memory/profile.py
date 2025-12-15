from __future__ import annotations

from typing import Dict, List


class ProfileMemory:
    def __init__(self) -> None:
        self._facts: Dict[str, Dict[str, str]] = {}

    def set_fact(self, session: str, key: str, value: str) -> None:
        facts = self._facts.setdefault(session, {})
        facts[key] = value

    def recall(self, session: str, limit: int = 20) -> List[dict]:
        facts = self._facts.get(session, {})
        items = list(facts.items())[:limit]
        return [{"key": k, "value": v} for k, v in items]
