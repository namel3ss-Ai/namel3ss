from __future__ import annotations

from typing import Dict, List


class ShortTermMemory:
    def __init__(self) -> None:
        self._messages: Dict[str, List[dict]] = {}

    def record(self, session: str, message: dict) -> None:
        messages = self._messages.setdefault(session, [])
        messages.append(message)

    def recall(self, session: str, limit: int) -> List[dict]:
        messages = self._messages.get(session, [])
        if limit <= 0:
            return []
        return messages[-limit:]
