from __future__ import annotations


RISK_LEVELS = ("low", "medium", "high")


def risk_from_summary(summary: dict[str, object], runner_default: str | None = None) -> str:
    levels = summary.get("levels") if isinstance(summary, dict) else {}
    if not isinstance(levels, dict):
        levels = {}
    filesystem = str(levels.get("filesystem", "none"))
    network = str(levels.get("network", "none"))
    env = str(levels.get("env", "none"))
    subprocess = str(levels.get("subprocess", "none"))
    secrets = summary.get("secrets") if isinstance(summary, dict) else []
    if runner_default == "container":
        return "high"
    if filesystem == "write" or subprocess == "allow":
        return "high"
    if filesystem == "read" or network == "outbound" or env == "read":
        return "medium"
    if isinstance(secrets, list) and secrets:
        return "medium"
    if filesystem not in {"none", "read", "write"}:
        return "high"
    if network not in {"none", "outbound"}:
        return "high"
    if env not in {"none", "read"}:
        return "high"
    if subprocess not in {"none", "allow"}:
        return "high"
    return "low"


def risk_rank(value: str) -> int:
    if value not in RISK_LEVELS:
        return len(RISK_LEVELS)
    return RISK_LEVELS.index(value)


__all__ = ["RISK_LEVELS", "risk_from_summary", "risk_rank"]
