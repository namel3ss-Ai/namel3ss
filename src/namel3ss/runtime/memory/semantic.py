from __future__ import annotations

from typing import Dict, List


class SemanticMemory:
    def __init__(self) -> None:
        self._snippets: Dict[str, List[str]] = {}

    def record(self, session: str, snippet: str) -> None:
        self._snippets.setdefault(session, []).append(snippet)

    def recall(self, session: str, query: str, top_k: int = 3) -> List[dict]:
        snippets = self._snippets.get(session, [])
        matches = []
        for text in snippets:
            score = 1 if query and query.lower() in text.lower() else 0
            matches.append({"text": text, "score": score})
        matches.sort(key=lambda x: x["score"], reverse=True)
        return matches[:top_k]
