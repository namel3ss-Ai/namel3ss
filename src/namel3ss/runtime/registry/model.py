from __future__ import annotations

from dataclasses import dataclass

from namel3ss.runtime.packs.risk import risk_from_summary


RISK_LEVELS = {"low", "medium", "high"}
SIGNATURE_STATUSES = {"verified", "unverified", "unsigned", "invalid"}


@dataclass(frozen=True)
class SignatureInfo:
    status: str
    algorithm: str | None


def normalize_entry(entry: dict[str, object]) -> dict[str, object]:
    normalized = dict(entry)
    for key in ("tools", "intent_tags", "intent_phrases", "verified_by"):
        normalized[key] = _sorted_str_list(normalized.get(key))
    normalized["capabilities"] = _normalize_capabilities(normalized.get("capabilities"))
    normalized["guarantees"] = _normalize_guarantees(normalized.get("guarantees"))
    normalized["intent_text"] = _intent_text(normalized)
    normalized["risk"] = _entry_risk(normalized)
    normalized["signature"] = _signature_info(normalized)
    return normalized


def entry_trusted(entry: dict[str, object]) -> bool:
    return bool(_sorted_str_list(entry.get("verified_by")))


def entry_risk(entry: dict[str, object]) -> str:
    return _entry_risk(entry)


def entry_signature(entry: dict[str, object]) -> SignatureInfo:
    info = _signature_info(entry)
    return SignatureInfo(status=str(info.get("status")), algorithm=info.get("algorithm"))  # type: ignore[arg-type]


def entry_intent_text(entry: dict[str, object]) -> str:
    return _intent_text(entry)


def _intent_text(entry: dict[str, object]) -> str:
    raw = entry.get("intent_text")
    if isinstance(raw, str) and raw.strip():
        return _normalize_text(raw)
    phrases = _sorted_str_list(entry.get("intent_phrases"))
    if phrases:
        return "\n".join(phrases)
    pack_name = entry.get("pack_name")
    if isinstance(pack_name, str) and pack_name.strip():
        return pack_name.strip()
    return ""


def _signature_info(entry: dict[str, object]) -> dict[str, object]:
    raw = entry.get("signature")
    if isinstance(raw, dict):
        status = raw.get("status")
        algorithm = raw.get("algorithm")
        if isinstance(status, str) and status in SIGNATURE_STATUSES:
            return {
                "status": status,
                "algorithm": str(algorithm) if algorithm else None,
            }
    verified_by = _sorted_str_list(entry.get("verified_by"))
    signer_id = entry.get("signer_id")
    if verified_by:
        status = "verified"
    elif isinstance(signer_id, str) and signer_id.strip():
        status = "unverified"
    else:
        status = "unsigned"
    return {"status": status, "algorithm": None}


def _entry_risk(entry: dict[str, object]) -> str:
    raw = entry.get("risk")
    if isinstance(raw, str) and raw in RISK_LEVELS:
        return raw
    capabilities = _normalize_capabilities(entry.get("capabilities"))
    summary = {
        "levels": {
            "filesystem": capabilities.get("filesystem", "none"),
            "network": capabilities.get("network", "none"),
            "env": capabilities.get("env", "none"),
            "subprocess": capabilities.get("subprocess", "none"),
        },
        "secrets": capabilities.get("secrets", []),
    }
    runner_default = None
    runner = entry.get("runner")
    if isinstance(runner, dict):
        value = runner.get("default")
        if isinstance(value, str):
            runner_default = value
    return risk_from_summary(summary, runner_default)


def _normalize_capabilities(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        return {
            "filesystem": "none",
            "network": "none",
            "env": "none",
            "subprocess": "none",
            "secrets": [],
        }
    secrets = _sorted_str_list(value.get("secrets"))
    return {
        "filesystem": str(value.get("filesystem") or "none"),
        "network": str(value.get("network") or "none"),
        "env": str(value.get("env") or "none"),
        "subprocess": str(value.get("subprocess") or "none"),
        "secrets": secrets,
    }


def _normalize_guarantees(value: object) -> dict[str, object] | None:
    if not isinstance(value, dict):
        return None
    normalized = dict(value)
    secrets = normalized.get("secrets_allowed")
    if isinstance(secrets, list):
        normalized["secrets_allowed"] = _sorted_str_list(secrets)
    return normalized


def _sorted_str_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return sorted({str(item) for item in value if isinstance(item, str) and item.strip()})


def _normalize_text(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")).strip()


__all__ = [
    "RISK_LEVELS",
    "SIGNATURE_STATUSES",
    "SignatureInfo",
    "entry_intent_text",
    "entry_risk",
    "entry_signature",
    "entry_trusted",
    "normalize_entry",
]
