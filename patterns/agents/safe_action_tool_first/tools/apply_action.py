def run(payload: dict) -> dict:
    action = str(payload.get("action") or "")
    target = str(payload.get("target") or "")
    approved = bool(payload.get("approved"))
    status = "applied" if approved else "blocked"
    return {
        "status": status,
        "action": action,
        "target": target,
        "message": f"{status}: {action} -> {target}",
    }
