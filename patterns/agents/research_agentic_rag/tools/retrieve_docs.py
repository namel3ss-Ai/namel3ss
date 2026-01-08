def run(payload: dict) -> dict:
    query_text = str(payload.get("query") or "")
    docs = [
        {
            "title": "Deterministic workflows",
            "url": "https://example.com/determinism",
            "snippet": f"Deterministic handling for: {query_text}",
        },
        {
            "title": "Tool-first orchestration",
            "url": "https://example.com/tool-first",
            "snippet": "Use tools to gather sources before synthesis.",
        },
        {
            "title": "Evidence discipline",
            "url": "https://example.com/evidence",
            "snippet": "Citations are listed in source order.",
        },
    ]
    return {"documents": docs}
